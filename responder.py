import time
from threading import Thread
from typing import Iterator, List


from BingImageCreator import ImageGen  # type: ignore
from telebot import TeleBot  # type: ignore
from telebot.types import InputMediaPhoto, Message  # type: ignore

from utils import get_quota, prepare_save_images, save_images


def respond_quota(
    bot: TeleBot, msg: Message, bing_image_obj_list: List[ImageGen]
) -> None:
    quota_string = "\n".join(
        [
            f"Cookie{index} left quota: {quota}."
            for index, quota in get_quota(bing_image_obj_list)
        ]
    )
    message: Message = bot.reply_to(
        msg,
        f"Quota stats: \nWe have {len(bing_image_obj_list)} cookies\n{quota_string}",
    )
    # delete it
    time.sleep(3)
    try:
        bot.delete_message(msg.chat.id, message.message_id)
        bot.delete_message(msg.chat.id, msg.message_id)
    except Exception as e:
        # just pass the it when error
        print(str(e))


def respond_prompt(
    bot: TeleBot,
    message: Message,
    bing_cookie_pool: Iterator[ImageGen],
    bing_cookie_cnt: int,
    prompt: str,
) -> None:
    # Find a cookie within the limit
    within_limit = False
    for _ in range(bing_cookie_cnt):
        image_obj = next(bing_cookie_pool)
        limit = image_obj.get_limit_left()
        if limit > 1:
            within_limit = True
            break
    info_message_id: Union[int, None] = None
    if not within_limit:
        # info message
        message: Message = bot.reply_to(
            message,
            "No cookie is with limit left, will wait a long time and maybe fail",
        )
        info_message_id: int = message.message_id
        # No return here, because we can still use the cookie with no limit left.
    else:
        # info message
        message: Message = bot.reply_to(
            message,
            f"Using bing DALL-E 3 generating images please wait, left times we can use: {limit-1}",
        )
        info_message_id: int = message.message_id

    # Generate the images
    try:
        images: List[str] = image_obj.get_images(prompt)
    except Exception as e:
        print(str(e))
        bot.reply_to(
            message,
            "Your prompt ban from Bing DALL-E 3, please change it and do not use the same prompt.",
        )
        return

    # Save the images locally
    save_path = prepare_save_images(message)
    Thread(target=save_images, args=(image_obj, images, save_path)).start()

    # Send the images
    photos_list = [InputMediaPhoto(i) for i in images]
    if photos_list:
        bot.send_media_group(
            message.chat.id,
            photos_list,
            reply_to_message_id=message.message_id,
            disable_notification=True,
        )
        # then delete the info message
        try:
            bot.delete_message(message.chat.id, info_message_id)
        except Exception as e:
            # just pass the it when error
            print(str(e))
            pass
    else:
        bot.reply_to(message, "Generate images error")
