[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
![GitHub Release (latest SemVer including pre-releases)](https://img.shields.io/github/v/release/ad-ha/kidschores-ha?include_prereleases)
![GitHub Downloads (all assets, latest release)](https://img.shields.io/github/downloads/ad-ha/kidschores-ha/latest/total)

[![GitHub Actions](https://github.com/ad-ha/kidschores-ha/actions/workflows/validate.yaml/badge.svg)](https://github.com/ad-ha/kidschores-ha/actions/workflows/validate.yaml)
[![Hassfest](https://github.com/ad-ha/kidschores-ha/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/ad-ha/kidschores-ha/actions/workflows/hassfest.yaml)


<h1>KidsChores</h1>

<p align="center">
  <img src="https://github.com/user-attachments/assets/e95bdb54-2c4c-4a84-96b4-f47a46a1228a" alt="KidsChores logo" width="300">
</p>
<p align="center">
  <a href="https://buymeacoffee.com/varetas3d" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174">
  </a>
</p>
<p>
  <br>
  <br>
</p>

KidsChores is a powerful Home Assistant integration that transforms family chore management into a fun, engaging, and secure experience. Designed with both kids and parents in mind, it helps you assign tasks, track progress, and reward achievements—all while keeping your data local and private.

**Important Notes:**  
- Please report any issues via [GitHub Issues](https://github.com/ad-ha/kidschores-ha/issues).  
- **Setup:** The integration must be configured through the Home Assistant wizard. Follow the installation steps carefully.

---

## INSTALLATION

### - **HACS (Home Assistant Community Store)**

1. **Ensure HACS is installed.** If you haven't yet installed HACS, follow the [HACS installation guide](https://hacs.xyz/docs/installation/manual).
2. In Home Assistant, navigate to **HACS**.
3. Click the three-dot menu in the top-right corner and select **"Custom repositories"**.  
   ![Add Repository](https://github.com/user-attachments/assets/0c36fafb-8b1f-424f-b9bb-3b32f674c0ea)
4. Enter the repository URL:  
   `https://github.com/ad-ha/kidschores-ha`
5. Select **"Integration"** from the Category dropdown and click **"ADD"**.  
![Select Category](https://github.com/user-attachments/assets/d5480cc6-efb1-4238-b5d1-a31193d3353d)
6. Search for **"KidsChores"** in HACS and install the integration.
7. **Restart Home Assistant** to apply the changes.

### - **Manual Installation**

1. Download the latest release from the [KidsChores GitHub repository](https://github.com/ad-ha/kidschores-ha/releases).
2. Unzip the downloaded file and copy the `kidschores` directory to the `custom_components` folder in your Home Assistant configuration directory.
3. **Restart Home Assistant** to recognize the new integration.

---

## CONFIGURATION

[<img src="https://github.com/user-attachments/assets/36459daa-a780-448a-82a5-19ee07ccd3f6" alt="Configuration Flow">](https://my.home-assistant.io/redirect/config_flow_start?domain=kidschores)

1. Go to **Configuration > Integrations** in Home Assistant.
2. Click **"+ Add Integration"** and search for **"KidsChores"**.
3. Follow the setup wizard:
- **Define Points Label:** Choose your points name (e.g., Stars, Bucks, Coins).
- **Add Kids & Parents:** Create profiles for your kids and assign parents.
- **Define Chores, Badges, Rewards, Penalties, Achievements, and Challenges:** Provide detailed settings such as names, descriptions, points, icons, due dates, and recurring schedules.
4. Finish the setup to start managing your kids’ chores and rewards directly from Home Assistant.
5. Use the **Options Flow** to edit, add, or delete any entities as needed.

---


## 🌟 Key Features

### 👧👦 Multi-User Management
- **Profile Creation & Customization:**  
  - Create and manage individual profiles for multiple kids and parents.
  - Track each child’s progress, achievements, and performance with ease.
  
- **Effortless Management:**  
  - Handle multiple kids with a single integration while monitoring individual statistics and trends.

### ⭐ CUSTOMIZABLE POINTS SYSTEM
  - Personalize the points system by choosing your own name and icon (e.g., Stars, Bucks, Coins) to better resonate with your family.

### 🧹 Chore Management
- **Assign & Track Chores:**  
  - Define chores with detailed descriptions, icons, due dates, and recurring schedules (daily, weekly, or monthly).  
  - Assign tasks to one or multiple kids and monitor each chore’s status *(pending, claimed, approved, overdue, etc.)* in real time.
  
- **Dynamic Chore States & Actions:**  
  - Leverage dynamic buttons to claim, approve, or disapprove chores—completion with built-in authorization and contextual notifications.
  - Monitor progress with sensors that update on a per-kid and global level.

### 🏅 Rewards, Badges, Achievements & Challenges
- **Automated Rewards & Incentives:**  
  - Award badges automatically when chore milestones are achieved.
  - Enhance kids motivation with badge points multipliers.
  - Track progress through streaks and cumulative totals, and even assign extra points for special achievements.
  
- **Reward Redemption:**  
  - Kids can redeem rewards using their earned points. Parental approval is required to finalize any reward, ensuring accountability.
  
### ⚖️ Penalty Application
- **Accountability Measures:**  
  - Apply penalties for missed chores or behavior, automatically adjusting points and encouraging responsibility.
  - Use penalty buttons for manual intervention when needed.

### 🔄 Recurring Chores
- **Scheduled Task Management:**  
  - Set up recurring chores with automated due date resets so that daily, weekly, or monthly tasks are always on track.

### 🔒 Parental Approval Workflows
- **Approval Processes:**  
  - Both chores and reward redemptions require parental approval, adding an extra layer of oversight.
  - Actionable notifications include contextual buttons (e.g., approve, disapprove and 30-minute reminder actions) to streamline the approval process.

### 📈 Detailed Statistics & Analytics
- **Comprehensive Sensors:**  
  - Track daily, weekly, monthly, and cumulative metrics on chore completions, points earned, rewards redeemed, badges awarded, penalties applied, and more.
  
- **Historical Data & Trends:**  
  - Analyze long-term progress to identify trends, celebrate improvements, or pinpoint areas that need attention.
  - Build your own statistics from the sensors available and options inside Home Assistant.

### 🛠 Customization & User-Friendly Interface
- **🛠 Dynamic Buttons & Actions:**  
  - Manage chores and points directly from the Home Assistant UI with buttons for claiming, approving, redeeming, and adjusting points.
  
- **🔧 Easy Setup & Maintenance:**  
  - Enjoy a user-friendly setup wizard and comprehensive configuration menus to add, edit, or delete kids, chores, badges, rewards, penalties, achievements, and challenges.
  
- **🌐 Multilingual Support:**  
  - Currently available in English and Spanish to cater to a diverse user base.

---

## 📸 Available Sensors & Buttons

### **Sensors**

#### Kid & Points Sensors
- **KidPointsSensor:** Displays each kid's total points.
- **KidPointsEarnedDaily/Weekly/MonthlySensor:** Monitor points earned over various time frames.
- **KidMaxPointsEverSensor:** Shows the highest points total ever reached by a kid.

#### Chore Sensors
- **CompletedChoresTotal/Daily/Weekly/MonthlySensor:** Track chore completions over different periods.
- **ChoreStatusSensor:** Displays the current status *(pending, claimed, approved, overdue)* for each chore and kid.
- **ChoreStreakSensor:** Tracks the current streak (in days) for a chore per kid.
- **SharedChoreGlobalStateSensor:** Provides a global view of shared chore statuses.

#### Badge, Reward & Penalty Sensors
- **KidBadgesSensor & KidHighestBadgeSensor:** Monitor the number of badges earned and the highest badge achieved.
- **BadgeSensor:** Individual sensor per badge, detailing threshold values and recipients.
- **RewardClaimsSensor, RewardApprovalsSensor & RewardStatusSensor:** Track reward claims, approvals, and current reward statuses per kid.
- **ChoreClaimsSensor & ChoreApprovalsSensor:** Count how many times a chore has been claimed or approved.
- **PenaltyAppliesSensor:** Logs the number of times each penalty is applied.

#### Approval & Progress Sensors
- **PendingChore/RewardApprovalsSensor:** Lists chores or rewards awaiting parental approval.
- **AchievementSensor & ChallengeSensor:** Provide details on specific achievements or challenges (including names, targets, rewards, and counts).
- **AchievementProgressSensor & ChallengeProgressSensor:** Show progress percentages toward each target per kid.
- **KidHighestStreakSensor:** Displays the highest current streak among streak-based achievements.

### **Buttons**

- **Chore Actions:**  
  Claim, approve, and disapprove chores directly from the Home Assistant interface.
  
- **Reward Actions:**  
  Redeem rewards, with subsequent parental approval steps built in.
  
- **Penalty & Points Adjustments:**  
  Apply penalties or adjust points (e.g., +1, -1, +10, -10) using dedicated buttons.
  
- **Workflow Buttons:**  
  Utilize contextual, actionable notifications to streamline approvals.

---

## 🚀 Options Flow

KidsChores includes an interactive Options Flow that lets you easily manage:
- **Kids & Parents**
- **Chores**
- **Badges**
- **Rewards**
- **Penalties**
- **Achievements**
- **Challenges**


---

## 🔐 Security & Privacy

- **Local Data Storage:**  
  All data is stored securely on your Home Assistant instance, ensuring your family’s information remains private.
  
- **No External Data Sharing:**  
  Your data never leaves your local network, keeping it safe from external access.

---

## 📢 Community

- **Community Feedback:**  
  Share your thoughts, feature requests, and improvements to help make KidsChores the ultimate family management tool.

---

KidsChores is designed to bring fun, structure, and accountability into your home. Whether you’re looking to better manage your kids’ daily routines or simply want to engage them with a rewarding system, KidsChores is here to help.

**Get started today and transform how your family handles chores, rewards, and more!**


---

## CONTRIBUTING

Contributions are very welcome! If you have suggestions or encounter any issues:
- Open an [issue](https://github.com/ad-ha/kidschores-ha/issues).
- Submit a [pull request](https://github.com/ad-ha/kidschores-ha/pulls).


---

## LICENSE

This project is licensed under the [GPL-3.0 license](LICENSE). See the LICENSE file for details.

---

## DISCLAIMER

THIS PROJECT IS NOT AFFILIATED WITH OR ENDORSED BY ANY OFFICIAL ENTITY. The information provided is for educational purposes only, and the developers assume no legal responsibility for the functionality or security of your devices.

   
