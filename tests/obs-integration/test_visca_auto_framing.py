"""PTZ Auto Framing: a camera that frames the people in its view by itself.

Its state key is "auto_framing", and a device that can set it has the
"auto_framing" feature. Its commands are a vendor's own, so the generic VISCA
command set leaves it out; Sony's SRG-A12 command set has it, as
8x 01 7e 04 3a 0p (1 start, 0 stop) and the 8x 09 7e 04 3a inquiry, which
ptzsim answers as one does (--visca-model 0001:0622).

The PTZ Controls dock turns it on and off from the camera's menu, and with
three hotkeys on the selected camera; the settings dialog's state view has a
checkbox for it. The menu isn't tested here: it is the dock's, which these
tests' OBS doesn't show, so nothing can be right-clicked in it. It turns
framing on and off as the hotkeys do, with PTZControls::setAutoFraming().
"""

import time

from test_visca_profiles import camera

SRG_A12 = {"model": "0001:0622", "flags": ()}
INQUIRY = "81097e043aff"


def a12(request, world, tmp_path):
    """A source with a VISCA filter on an SRG-A12 of its own: the sim, and
    the device, once it has read whether the camera is framing"""
    sim, state, device = camera(request, world, tmp_path, sim_args=SRG_A12,
                                read={"auto_framing", "power_on", "zoom_pos"})
    assert state["auto_framing"] is False
    return sim, device


def framing(sim):
    return sim.state()["visca"]["auto_framing"]


def wait_until_framing(world, sim, device, tmp_path, on):
    """Waits for the camera to be framing, or not, and the device to have
    read it back"""
    sim.wait_for(lambda s: s["visca"]["auto_framing"] is on)
    world.wait_for_device_state(device, tmp_path / "state.json",
                                lambda r: r["state"].get("auto_framing") is on, timeout=5)


def test_an_srg_a12_can_frame(request, obs_world, tmp_path):
    sim, device = a12(request, obs_world, tmp_path)
    state = obs_world.device_state(device)["state"]
    assert (state["vendor_id"], state["model_id"]) == (0x0001, 0x0622)
    assert state["features"].get("auto_framing") is True
    # long enough for the rest of what there is to read to have been: the
    # command set asks for nothing the camera hasn't
    time.sleep(2)
    assert sim.syntax_errors() == 0


def test_framing_is_turned_on_and_off_with_its_state(request, obs_world, tmp_path):
    sim, device = a12(request, obs_world, tmp_path)
    obs_world.set_device_state(device, auto_framing=True)
    wait_until_framing(obs_world, sim, device, tmp_path, True)
    obs_world.set_device_state(device, auto_framing=False)
    wait_until_framing(obs_world, sim, device, tmp_path, False)


def test_a_camera_of_no_such_model_is_never_asked(request, obs_world, tmp_path):
    """The generic command set, and the SRG-120DH's, which an SRG-A12 was
    used with before it had one of its own, have no auto framing: the camera
    isn't asked, and the device can't frame, though ptzsim could"""
    for model in ("0001:0000", "0001:0511"):
        sim, state, device = camera(request, obs_world, tmp_path, sim_args={"model": model, "flags": ()},
                                    read={"power_on", "zoom_pos", "wb_mode"})
        time.sleep(2)
        later = obs_world.device_state(device)["state"]
        assert "auto_framing" not in later, model
        assert "auto_framing" not in later["features"], model
        assert INQUIRY not in sim.state()["visca_inquiries"], model


def test_the_hotkeys_frame_the_selected_camera(request, obs_world, tmp_path):
    sim, device = a12(request, obs_world, tmp_path)
    obs_world.select_in_dock(device)
    obs_world.fire_hotkey("PTZ.AutoFramingOn")
    wait_until_framing(obs_world, sim, device, tmp_path, True)
    # on again leaves it on
    obs_world.fire_hotkey("PTZ.AutoFramingOn")
    time.sleep(0.5)
    assert framing(sim) is True
    obs_world.fire_hotkey("PTZ.AutoFramingToggle")
    wait_until_framing(obs_world, sim, device, tmp_path, False)
    obs_world.fire_hotkey("PTZ.AutoFramingToggle")
    wait_until_framing(obs_world, sim, device, tmp_path, True)
    obs_world.fire_hotkey("PTZ.AutoFramingOff")
    wait_until_framing(obs_world, sim, device, tmp_path, False)


def test_the_hotkeys_do_nothing_to_a_camera_that_cant_frame(request, obs_world, tmp_path):
    """A camera without the feature is sent nothing: ptzsim could frame, but
    the generic command set has no command for it"""
    sim, state, device = camera(request, obs_world, tmp_path, sim_args={"model": "0001:0000", "flags": ()},
                                read={"power_on", "zoom_pos"})
    obs_world.select_in_dock(device)
    for name in ("PTZ.AutoFramingOn", "PTZ.AutoFramingToggle"):
        obs_world.fire_hotkey(name)
    time.sleep(1)
    assert framing(sim) is False
    assert sim.syntax_errors() == 0


def test_the_hotkeys_are_listed(obs_world):
    for text in ("Toggle PTZ Auto Framing", "Set PTZ Auto Framing On", "Set PTZ Auto Framing Off"):
        assert obs_world.hotkey_listed(text), text


def test_the_state_view_has_a_checkbox_for_it(request, obs_world, tmp_path):
    sim, device = a12(request, obs_world, tmp_path)
    obs_world.open_settings_dialog(device)
    obs_world.wait_for_settings_dialog(None, lambda d: d["shown"].get("auto_framing") is False)
    obs_world.edit_dialog_state(auto_framing=True)
    wait_until_framing(obs_world, sim, device, tmp_path, True)
    obs_world.wait_for_settings_dialog(None, lambda d: d["shown"].get("auto_framing") is True)
    obs_world.edit_dialog_state(auto_framing=False)
    wait_until_framing(obs_world, sim, device, tmp_path, False)
