from your_pipeline.flows.repricing_flow import repricing_flow

def main():
    """
    Local scheduler using Prefect's `flow.serve()`:
      • Runs the flow daily at 03:00 based on your MACHINE'S timezone.
      • Starts a temporary Prefect server automatically.
      • Stop with Ctrl+C.

    Want 03:00 Asia/Manila regardless of your PC timezone?
      • Either set your OS timezone to Asia/Manila,
      • or switch to a worker-style deployment with a schedule timezone.
    """
    repricing_flow.serve(
        name="repricing-daily-local",
        cron="0 3 * * *",
        parameters={},
    )

if __name__ == "__main__":
    main()
