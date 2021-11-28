import frappe
from frappe import _
from chat.utils import update_room, is_user_allowed_in_room, raise_not_authorized_error


@frappe.whitelist(allow_guest=True)
def send(content, user, room, email):
    """Send the message via socketio

    Args:
        message (str): Message to be sent.
        user (str): Sender's name.
        room (str): Room's name.
        email (str): Sender's email.
    """
    if not is_user_allowed_in_room(room, email, user):
        raise_not_authorized_error()

    new_message = frappe.get_doc({
        'doctype': 'Chat Message',
        'content': content,
        'sender': user,
        'room': room,
        'sender_email': email
    }).insert()
    update_room(room=room, last_message=content)

    result = {
        'content': content,
        'user': user,
        'creation': new_message.creation,
        'room': room,
        'sender_email': email
    }

    typing_data = {
        'room': room,
        'user': user,
        'is_typing': 'false',
        'is_guest': 'true' if user == 'Guest' else 'false',
    }
    typing_event = room + ':typing'

    frappe.publish_realtime(event=room, message=result, after_commit=True)

    frappe.publish_realtime(event='latest_chat_updates',
                            message=result, after_commit=True)
    frappe.publish_realtime(event=typing_event,
                            message=typing_data, after_commit=True)


@frappe.whitelist(allow_guest=True)
def get_all(room, email):
    """Get all the messages of a particular room

    Args:
        room (str): Room's name.

    """
    if not is_user_allowed_in_room(room, email):
        raise_not_authorized_error()

    result = frappe.db.get_all('Chat Message',
                               filters={
                                   'room': room,
                               },
                               fields=['content', 'sender',
                                       'creation', 'sender_email'],
                               order_by='creation asc'
                               )
    return result


@frappe.whitelist()
def mark_as_read(room):
    """Mark the message as read

    Args:
        room (str): Room's name.
    """
    frappe.enqueue('chat.utils.update_room', room=room,
                   is_read=1, update_modified=False)


@frappe.whitelist(allow_guest=True)
def set_typing(room, user, is_typing, is_guest):
    """Set the typing text accordingly

    Args:
        room (str): Room's name.
        user (str): Sender who is typing.
        is_typing (bool): Whether user is typing.
        is_guest (bool): Whether user is guest or not.
    """
    result = {
        'room': room,
        'user': user,
        'is_typing': is_typing,
        'is_guest': is_guest
    }
    event = room + ':typing'
    frappe.publish_realtime(event=event,
                            message=result)
