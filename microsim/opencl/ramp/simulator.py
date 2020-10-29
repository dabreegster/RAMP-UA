import numpy as np
import pyopencl as cl
import pandas as pd
import os

from microsim.opencl.ramp.buffers import Buffers
from microsim.opencl.ramp.kernels import Kernels
from microsim.opencl.ramp.params import Params
from microsim.opencl.ramp.snapshot import Snapshot
from microsim.opencl.ramp.disease_statuses import DiseaseStatus


class Simulator:
    """
    Class to manage all OpenCL owned simulator state. Including methods to transfer data buffers to/from OpenCL devices
    and a step() method to execute the kernels to calculate one timestep of the model.
    """

    def __init__(self, snapshot, gpu=True, kernel_dir="microsim/opencl/ramp/kernels/"):
        """Initialise OpenCL context, kernels, and buffers for the simulator.

        Args:
            snapshot (Snapshot): snapshot containing data and number of places, people and slots
            gpu (bool): Whether to try to use a discrete GPU, set to false to use CPU.

        Raises:
            OSError: If a GPU was requested but none is found.
        """
        nplaces = snapshot.nplaces
        npeople = snapshot.npeople
        nslots = snapshot.nslots

        # Create an OpenCL context
        dev_type = cl.device_type.GPU if gpu else cl.device_type.CPU
        platform = None
        for plat in cl.get_platforms():
            if len(plat.get_devices(dev_type)) > 0:
                platform = plat
                break
        if platform is None:
            raise OSError("No compatible device found")
        ctx = cl.Context(dev_type=dev_type, properties=[(cl.context_properties.PLATFORM, platform)])
        queue = cl.CommandQueue(ctx)

        # Initialise the device buffers
        buffers = Buffers(
            place_activities=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, nplaces * 4),
            place_coords=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, nplaces * 8),
            place_hazards=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, nplaces * 4),
            place_counts=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, nplaces * 4),

            people_ages=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople * 2),
            people_obesity=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople * 2),
            people_cvd=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople),
            people_diabetes=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople),
            people_blood_pressure=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople),
            people_statuses=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople * 4),
            people_transition_times=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople * 4),
            people_place_ids=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople * nslots * 4),
            people_baseline_flows=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople * nslots * 4),
            people_flows=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople * nslots * 4),
            people_hazards=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople * 4),
            people_prngs=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, npeople * 16),

            params=cl.Buffer(ctx, cl.mem_flags.READ_WRITE, Params().num_bytes()),
        )

        # Load the OpenCL kernel programs
        with open(os.path.join(kernel_dir, "ramp_ua.cl")) as f:
            program = cl.Program(ctx, f.read())
            program.build(options=[f"-I {kernel_dir}"])

        kernels = Kernels(
            places_reset=program.places_reset,
            people_update_flows=program.people_update_flows,
            people_send_hazards=program.people_send_hazards,
            people_recv_hazards=program.people_recv_hazards,
            people_update_statuses=program.people_update_statuses)

        # Pass data buffers to the kernels using set_args
        kernels.places_reset.set_args(nplaces, buffers.place_hazards, buffers.place_counts)

        kernels.people_update_flows.set_args(
            npeople, nslots, buffers.people_statuses, buffers.people_baseline_flows,
            buffers.people_flows, buffers.people_place_ids, buffers.place_activities,
            buffers.params)

        kernels.people_send_hazards.set_args(
            npeople, nslots, buffers.people_statuses, buffers.people_place_ids,
            buffers.people_flows, buffers.people_hazards, buffers.place_hazards,
            buffers.place_counts, buffers.place_activities, buffers.params)

        kernels.people_recv_hazards.set_args(
            npeople, nslots, buffers.people_statuses, buffers.people_place_ids,
            buffers.people_flows, buffers.people_hazards, buffers.place_hazards,
            buffers.params)

        kernels.people_update_statuses.set_args(
            npeople, buffers.people_ages, buffers.people_obesity, buffers.people_cvd, buffers.people_diabetes,
            buffers.people_blood_pressure, buffers.people_hazards, buffers.people_statuses,
            buffers.people_transition_times, buffers.people_prngs, buffers.params)

        self.nplaces = nplaces
        self.npeople = npeople
        self.nslots = nslots
        self.time = snapshot.time

        self.platform = platform
        self.ctx = ctx
        self.queue = queue
    
        self.start_snapshot = snapshot
        self.buffers = buffers
        self.kernels = kernels

    def platform_name(self):
        """The name of the OpenCL platform being used for simulation."""
        return self.platform.get_info(cl.platform_info.NAME)

    def device_name(self):
        """The name of the OpenCL device being used for simulation."""
        device = self.ctx.get_info(cl.context_info.DEVICES)[0]
        return device.get_info(cl.device_info.NAME)

    def upload(self, name, host_buffer):
        """Transfers the contents of the provided numpy array to the named OpenCL buffer."""
        if hasattr(self.buffers, name):
            cl.enqueue_copy(self.queue, getattr(self.buffers, name), host_buffer)
        else:
            raise ValueError("No buffer with name {}".format(name))

    def download(self, name, host_buffer):
        """Transfers the contents of the named OpenCL buffer to the provided numpy array."""
        if hasattr(self.buffers, name):
            cl.enqueue_copy(self.queue, host_buffer, getattr(self.buffers, name))
        else:
            raise ValueError("No buffer with name {}".format(name))

    def upload_all(self, host_buffers):
        """Upload to every device buffer, errors if host_buffers is missing a field.

        Args:
            host_buffers: A Buffers namedtuple containing numpy arrays.
        """
        for name in Buffers._fields:
            self.upload(name, getattr(host_buffers, name))

    def download_all(self, host_buffers):
        """Downloads every device buffer, errors if host_buffers is missing a field.

        Args:
            host_buffers: A dict of string names to numpy buffers.
        """
        for name in Buffers._fields:
            self.download(name, getattr(host_buffers, name))

    def step(self):
        """Runs each kernel in order and updates the time. Blocks until complete."""
        reset_event = cl.enqueue_nd_range_kernel(
            self.queue, self.kernels.places_reset, (self.nplaces,), None)
        update_flows_event = cl.enqueue_nd_range_kernel(
            self.queue, self.kernels.people_update_flows, (self.npeople,), None)
        event = cl.enqueue_nd_range_kernel(
            self.queue, self.kernels.people_send_hazards, (self.npeople,), None,
            wait_for=[reset_event, update_flows_event])
        event = cl.enqueue_nd_range_kernel(
            self.queue, self.kernels.people_recv_hazards, (self.npeople,), None, wait_for=[event])
        event = cl.enqueue_nd_range_kernel(
            self.queue, self.kernels.people_update_statuses, (self.npeople,), None, wait_for=[event])
        event.wait()
        self.time += np.uint32(1)

    def step_kernel(self, name):
        """Run a single kernel specified by name. NB: this is intended only to be used for testing."""
        if hasattr(self.kernels, name):
            dims = (self.nplaces,) if name == "places_reset" else (self.npeople,)
            event = cl.enqueue_nd_range_kernel(self.queue, getattr(self.kernels, name), dims, None)
            event.wait()
        else:
            raise ValueError("No kernel with name {}".format(name))
    
    def seed_initial_infections(self, num_seed_days=5, data_dir="microsim/opencl/data/"):
        """
        Seeds initial infections by assigning initial cases based on the GAM assigned cases data.
        The cases for the first num_seed_days days are all seeded at once, eg. they are in the snapshot before the
        simulation is run.
        Initial cases are assigned to people from higher risk area codes who spend more time outside of their home.
        """

        # load initial case data
        initial_cases = pd.read_csv(os.path.join(data_dir, "devon_initial_cases.csv"))

        msoa_risks_df = pd.read_csv(os.path.join(data_dir, "msoas.csv"), usecols=[1, 2])

        # combine into a single dataframe to allow easy filtering based on high risk area codes and
        # not home probabilities
        people_df = pd.DataFrame({"area_code": self.start_snapshot.area_codes,
                                  "not_home_prob": self.start_snapshot.not_home_probs})
        people_df = people_df.merge(msoa_risks_df, on="area_code")

        # get people_ids for people in high risk MSOAs and high not home probability
        high_risk_ids = np.where((people_df["risk"] == "High") & (people_df["not_home_prob"] > 0.3))[0]
        
        max_hazard_val = np.finfo(np.float32).max
        
        for day in range(num_seed_days):
            # randomly choose a given number of cases from the high risk people ids.
            num_cases = initial_cases.loc[day, "num_cases"]
            initial_case_ids = np.random.choice(high_risk_ids, num_cases)

            people_hazards = np.zeros(self.npeople, dtype=np.float32)

            # set hazard to maximum float val, so these people will have infection_prob=1
            # and will transition to exposed state
            people_hazards[initial_case_ids] = max_hazard_val

            self.upload("people_hazards", people_hazards)

            # run only the update statuses kernel so that people transition through disease states
            self.step_kernel("people_update_statuses")

        self.time = num_seed_days
