from model import simulate
import time

if __name__ == "__main__":
    start = time.time()
    df = simulate(
        share_generation=[1 + i / 20 for i in range(0, 21)],
        share_renewable=[0 + i / 20 for i in range(0, 21)],
        share_storage=[0 + i / 100 for i in range(0, 21)],
        fn_out="./data/results.parquet",
    )
    end = time.time()
    print(f"Time taken: {end - start}")
    print("hello")
