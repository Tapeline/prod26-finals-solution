-- Converted to atomic lua script by Gemini 3 Pro
-- Edited manually

local cooldown_key = KEYS[1]
local last_reset_key = KEYS[2]
local now = tonumber(ARGV[1])
local cooldown_after_s = tonumber(ARGV[2])
local cooldown_for_s = tonumber(ARGV[3])

if redis.call("EXISTS", cooldown_key) == 1 then
    return 1
end

local last_reset = redis.call("GET", last_reset_key)

if not last_reset then
    redis.call("SET", last_reset_key, now, "EX", cooldown_after_s * 2) 
    return 0
end

if (now - tonumber(last_reset)) >= cooldown_after_s then
    redis.call("SET", cooldown_key, "1", "EX", cooldown_for_s)
    redis.call("SET", last_reset_key, now, "EX", cooldown_after_s * 2)
    return 1
end

return 0