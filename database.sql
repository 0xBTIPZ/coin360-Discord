CREATE TABLE `guild_list` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `guild_id` varchar(64) NOT NULL,
  `channel_id` varchar(32) NOT NULL,
  `assigned_date` int(11) NOT NULL,
  `assigned_by_id` varchar(32) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `guild_id` (`guild_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
