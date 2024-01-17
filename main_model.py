from model import simulate
import time

if __name__ == "__main__":
    start = time.time()
    df = simulate(
        share_generation=[1 + i / 10 for i in range(0, 6)],
        share_renewable=[0 + i / 10 for i in range(0, 11)],
        share_storage=[0 + i / 50 for i in range(0, 11)],
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
