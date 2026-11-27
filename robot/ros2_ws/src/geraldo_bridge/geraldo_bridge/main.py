def main() -> None:
    """Sobe a ponte em 127.0.0.1:8765. Rode com o ROS carregado e o Python do venv do app: `python -m geraldo_bridge.main`."""
    import uvicorn

    from .gazebo_gui import GazeboGui
    from .ros_adapter import RclpyRosPort
    from .server import HOST, PORT, create_app
    from .state import BridgeState

    state, port, gui = BridgeState(), RclpyRosPort(), GazeboGui()
    port.start(state)
    # a janela do Gazebo e o rclpy fecham no lifespan do app (server.py), que o uvicorn roda no SIGTERM e no SIGINT
    uvicorn.run(create_app(state, port, gui), host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
