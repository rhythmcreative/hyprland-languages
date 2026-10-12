<h1 align="center">Hyprland Languages</h1>

<div align="center">
 
[![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793d1?style=for-the-badge&logo=archlinux&logoColor=white "Arch Linux")](https://archlinux.org/)
[![Debian](https://img.shields.io/badge/Debian-A81D33?style=for-the-badge&logo=debian&logoColor=white "Debian")](https://www.debian.org/)
[![Fedora](https://img.shields.io/badge/Fedora-51A2DA?style=for-the-badge&logo=fedora&logoColor=white "Fedora")](https://fedoraproject.org/)
[![Hyprland](https://img.shields.io/badge/Hyprland-00c853?style=for-the-badge&logo=wayland&logoColor=white "Hyprland")](https://hyprland.org/)

</div>

<div align="center">
 <p><i>High-performance locale and keyboard layout manager for Hyprland with sub-5ms search across all 500+ locales from /etc/locale.gen and 99+ XKB layouts.</i></p>
</div>

[![Typing SVG](https://readme-typing-svg.herokuapp.com?font=Fira+Code&pause=1000&color=F7F7F7&vCenter=true&multiline=true&width=435&height=35&lines=HOW+TO+INSTALL+)](https://git.io/typing-svg)

To install, clone the repository and run the `install.sh` script:

```bash
git clone https://github.com/rhythmcreative/hyprland-languages.git
cd hyprland-languages
./install.sh
```

> [!IMPORTANT]
> **Run the script as a normal user**. The script will link the binary to `~/.local/bin` and link the Python library to your user environment. Do not run it with `sudo ./install.sh`.

[![Typing SVG](https://readme-typing-svg.herokuapp.com?font=Fira+Code&pause=1000&color=F7F7F7&vCenter=true&multiline=true&width=435&height=35&lines=HOW+TO+USE+)](https://git.io/typing-svg)

### System Status
```bash
# View active locale & keyboard status
hyprland-languages status

# Get JSON format (for Quickshell, Waybar, scripts)
hyprland-languages status --json
```

### Locale Management (`/etc/locale.gen`)
```bash
# Search any locale by language, country, or code
hyprland-languages locales search spanish
hyprland-languages locales search de_DE

# Generate a locale in /etc/locale.gen and run locale-gen
hyprland-languages locales generate de_DE.UTF-8

# Set user locale (persists across reboots in ~/.config/environment.d/10-locale.conf)
hyprland-languages locales set es_ES.UTF-8
```

### Keyboard Layouts (XKB)
```bash
# Search keyboard layouts
hyprland-languages layouts search german

# Switch layout across all connected keyboards
hyprland-languages layouts switch es

# Cycle to next or previous layout
hyprland-languages layouts next
hyprland-languages layouts prev

# Add or remove layout from Hyprland config
hyprland-languages layouts add de
hyprland-languages layouts remove de
```

[![Typing SVG](https://readme-typing-svg.herokuapp.com?font=Fira+Code&pause=1000&color=F7F7F7&vCenter=true&multiline=true&width=435&height=35&lines=UNINSTALL)](https://git.io/typing-svg)

To remove the application, binary links, and cache:

```bash
./uninstall.sh
```
