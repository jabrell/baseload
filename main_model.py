from model import simulate
import time
import numpy as np

if __name__ == "__main__":
    start = time.time()
    df = simulate(
        share_generation=np.arange(1, 1.25, 0.05),
        share_renewable=np.arange(0, 1.1, 0.1),
        share_storage=np.arange(0, 0.00011, 0.00001),
        cost_curtailment=[
            {"nuclear": 1, "renewable": 0},
            {"nuclear": 0, "renewable": 1},
        ],
        total_demand=100,
        fn_out="./data/results.parquet",
        country="DE",
        start="2017/06/01 00:00",
        end="2018/05/31 23:00",
    )
    end = time.time()
    print(f"Time taken: {end - start}")
    print("Finished!")
