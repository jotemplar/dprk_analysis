search_packs = {
    # ——— Existing categories (trim if you’re duplicating elsewhere) ———
    "Refugees_Communities": [
        # EN / RU / KR / ZH
        '"North Korean refugees" Russia (community OR association OR church OR NGO) (photo OR image) 2020..2025',
        '"северокорейские беженцы" Россия (сообщество OR диаспора OR церковь OR НКО) (фото) 2020..2025',
        '러시아 "북한 난민" (커뮤니티 OR 공동체 OR 교회 OR NGO) (사진) 2020..2025',
        '俄罗斯 "朝鲜 难民" (社区 OR 侨民 OR 教会 OR NGO) (照片) 2020..2025',
        # Asylum & disappearance
        'Russia "North Korean asylum" (application OR detained OR disappeared) (photo) 2020..2025',
        'Россия "северокорейцы" (убежище OR исчезновение OR задержан) (фото) 2020..2025',
        # Site-scoped platforms
        'site:t.me ("северокорей" OR "КНДР") (беженц OR диаспор)',
        'site:vk.com ("северокорейцы" OR "КНДР") (сообщество OR группа)',
        'site:ok.ru ("северокорейцы" группа)',
        'site:bezformata.com ("северокорейцы" OR КНДР) (диаспора OR беженц)',
        # Context URL (labor tag for broader worker/abuse items)
        'https://www.dailynk.com/english/tag/labor/'
    ],

    "Phones_Chinese_Forums": [
        # EN
        'Russia forums "Chinese phones" North Korea (WeChat OR SIM) (thread OR forum) 2020..2025',
        '("Chinese phone" OR "dual SIM") North Korea Russia border (WeChat) discussion 2020..2025',
        # RU
        '"китайские телефоны" Северная Корея (граница OR Хесан) форум 2020..2025',
        '"телефон для КНДР" купить ("сим-карта Китай" OR WeChat) форум 2020..2025',
        # RU forums & classifieds (site-scoped)
        'site:4pda.* ("КНДР" OR "Северная Корея") ("китайский телефон" OR WeChat OR "китайская сим")',
        'site:avito.ru ("китайский телефон" AND ("граница" OR "КНДР"))',
        'site:vk.com ("китайский телефон" AND КНДР)',
        'site:ok.ru ("КНДР" телефон)',
        # KR
        '러시아 포럼 "중국폰" "북한" (위챗 OR 중국 심) 2020..2025',
        # ZH
        '俄罗斯 论坛 "中国 手机" 朝鲜 (微信 OR SIM) 讨论 2020..2025',
        'site:tieba.baidu.com "朝鲜 手机" 俄罗斯 微信'
    ],

    "Locating_Workers_Region": [
        # General
        '"North Korean workers" Russia (warehouse OR construction OR dorms) (photo) 2021..2025',
        '"северокорейские рабочие" Россия (склад OR стройка OR общежитие) (фото) 2021..2025',
        '러시아 "북한 노동자" (창고 OR 건설 OR 기숙사) (사진) 2021..2025',
        '俄罗斯 "朝鲜 工人" (仓库 OR 建筑 OR 宿舍) (图片) 2021..2025',
        # Women in warehouses
        '"North Korean women" Russia e-commerce warehouse (video OR photo) 2024..2025',
        '"северокорейские женщины" Россия (склад маркетплейс) (видео OR фото) 2024..2025',
        # Site-scoped by platform/region
        'site:t.me (Северокорей* OR КНДР) (склад OR общежитие OR стройка) 2024..2025',
        'site:vk.com (КНДР OR "северокорейские") (Владивосток OR Приморский край OR Курск)',
        'site:ok.ru (северокорейцы AND Курск)',
        'site:bezformata.com (КНДР OR "северокорей") (Приморский OR Владивосток)',
        'site:kurskweb.ru "северокорейские рабочие"'
    ],

    "Abuse_Exploitation_Asylum": [
        # EN
        '"North Korean workers" Russia (abuse OR exploited OR "forced labor") (photo) 2021..2025',
        'Russia "North Korean workers" ("withheld wages" OR surveillance OR repatriated) (photo) 2022..2025',
        '"North Korean asylum" Russia (detained OR disappeared) (photo) 2020..2025',
        # RU
        '"северокорейские рабочие" Россия (эксплуатация OR "принудительный труд" OR насилие) (фото) 2021..2025',
        'Россия "рабочие из КНДР" ("невыплата зарплаты" OR слежка OR репатриация) (фото) 2022..2025',
        # KR
        '러시아 "북한 노동자" (학대 OR 착취 OR "강제노동") (사진) 2021..2025',
        '러시아 "북한 노동자" (임금 체불 OR 감시 OR 송환) (사진) 2022..2025',
        # ZH
        '俄罗斯 "朝鲜 工人" (虐待 OR 剥削 OR "强迫 劳动") (图片) 2021..2025',
        '俄罗斯 "朝鲜 工人" ("拖欠 工资" OR 监控 OR 遣返) (照片) 2022..2025',
        # Site-scoped
        'site:t.me (КНДР OR "северокорей") (эксплуатация OR "принудительный труд" OR беженц)',
        'site:vk.com ("северокорейские рабочие" OR КНДР) (эксплуатация OR "принудительный труд")',
        'site:ok.ru ("северокорейские" AND эксплуатация)',
        'site:bezformata.com ("КНДР" AND труд)'
    ],

    # ——— NEW: groups to check (with direct URLs and scoped queries) ———
    "Groups_to_Check": [
        # Direct URLs
        'https://vk.com/solidarity_dprk',
        'https://spbaic.ru/ru/org_structure/obshhestvo-rossijsko-korejskoj-druzhby/',
        'https://vk.com/dprk_solidarity_group',
        # Site-scoped variants to surface posts, photos, events, member lists
        'site:vk.com/solidarity_dprk (фото OR видео OR встреча OR мероприятие)',
        'site:vk.com/dprk_solidarity_group (фото OR обсуждение OR встреча OR набор)',
        'site:spbaic.ru "Общество российско-корейской дружбы" (мероприятие OR фото OR отчёт)'
    ],

    # ——— NEW: hiring DPRK workers (queries + supplied URLs) ———
    "Hiring_DPRK_Workers": [
        # English anchors
        '"how to hire DPRK workers" Russia 2020..2025',
        '"hire North Korean workers" Russia agency 2020..2025',
        # Russian queries (common phrasings)
        '"как нанять рабочих из КНДР" 2020..2025',
        '"как оформить рабочих из КНДР" 2020..2025',
        '"где взять рабочих из КНДР" 2020..2025',
        '"наём северокорейских работников" Россия 2020..2025',
        '"рабочие из КНДР" подрядчики Россия 2020..2025',
        # Site-scoped: business associations, HR portals, tenders
        'site:mmc-rspp.ru ("рабочие из КНДР" OR КНДР) 2020..2025',
        'site:hh.ru ("КНДР" OR "северокорейские") работники 2020..2025',
        'site:zakupki.gov.ru КНДР рабочие 2020..2025',
        'site:vc.ru КНДР рабочие наём 2020..2025',
        # Corporate case: Wildberries hiring NK workers
        'site:thehrd.ru Wildberries "Северной Кореи" нанимат* 2020..2025',
        'site:news.* Wildberries "северокорейских" сотрудниц 2024..2025',
        # Supplied URLs
        'https://mmc-rspp.ru/m/staff/scan/line/%D0%B3%D0%B4%D0%B5-%D0%B2%D0%B7%D1%8F%D1%82%D1%8C-%D1%80%D0%B0%D0%B1%D0%BE%D1%87%D0%B8%D0%B5-%D0%B8%D0%B7-%D0%BA%D0%BD%D0%B4%D1%80',
        'https://thehrd.ru/news/wildberries-nachal-nanimat-sotrudnic-iz-severnoj-korei-pilotnyj-proekt-ili-massovyj-najm/'
    ],

    # ——— Optional: corporate / warehouse case focus ———
    "Corporate_Warehouse_Cases": [
        # General EN/RU/KR/ZH variants focused on marketplaces/logistics
        '"North Korean women" Russia (warehouse OR marketplace) Wildberries (photo OR video) 2024..2025',
        '"северокорейские женщины" (склад OR маркетплейс) Wildberries (фото OR видео) 2024..2025',
        '러시아 "북한 여성" (물류창고 OR 마켓플레이스) (영상 OR 사진) 2024..2025',
        '俄罗斯 "朝鲜 女工" (仓库 OR 平台) (视频 OR 照片) 2024..2025',
        # Platform/site scoped
        'site:t.me (Вайлдберриз OR Wildberries) ("северокорей" OR КНДР) (склад OR сотрудниц*)',
        'site:vk.com (Wildberries OR Вайлдберриз) ("северокорей" OR КНДР) (склад OR набор)',
        'site:ok.ru (Вайлдберриз AND сотрудниц* AND КНДР)'
    ]
}