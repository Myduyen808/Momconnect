'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { MessageCircle, X, Send, Users } from 'lucide-react'

interface SimpleUser {
  id: string
  name: string
}

export default function SimpleChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [showFriends, setShowFriends] = useState(true)
  const [message, setMessage] = useState('')
  const [unreadCount, setUnreadCount] = useState(3)

  const toggleChat = () => {
    setIsOpen(!isOpen)
  }

  const selectFriend = (friendId: string) => {
    setShowFriends(false)
    console.log('Selected friend:', friendId)
  }

  const backToFriends = () => {
    setShowFriends(true)
  }

  const sendMessage = () => {
    if (message.trim()) {
      console.log('Sending message:', message)
      setMessage('')
    }
  }

  const friends: SimpleUser[] = [
    { id: '1', name: 'Mẹ Bé 2' },
    { id: '2', name: 'Mẹ Bé 3' },
    { id: '3', name: 'Mẹ Bé 4' }
  ]

  return (
    <>
      {/* Chat Button */}
      <div className="fixed bottom-4 right-4 z-50">
        <Button
          onClick={toggleChat}
          className="w-14 h-14 rounded-full bg-blue-500 hover:bg-blue-600 relative"
        >
          <MessageCircle className="w-6 h-6" />
          {unreadCount > 0 && (
            <Badge className="absolute -top-1 -right-1 bg-red-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center">
              {unreadCount}
            </Badge>
          )}
        </Button>
      </div>

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-20 right-4 w-80 z-50">
          <div className="bg-white rounded-lg shadow-2xl border">
            {/* Header */}
            <div className="bg-blue-500 text-white p-4 rounded-t-lg flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                <span className="font-semibold">
                  {showFriends ? 'Bạn bè' : 'Đang chat'}
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsOpen(false)}
                className="text-white hover:bg-white/20 h-8 w-8 p-0"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* Content */}
            <div className="h-96">
              {showFriends ? (
                // Friends List
                <div className="p-4">
                  <h3 className="font-medium mb-3">Chọn bạn bè để chat</h3>
                  {friends.map(friend => (
                    <div
                      key={friend.id}
                      onClick={() => selectFriend(friend.id)}
                      className="flex items-center gap-3 p-3 hover:bg-gray-100 rounded cursor-pointer"
                    >
                      <div className="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center">
                        {friend.name.charAt(0)}
                      </div>
                      <span className="flex-1">{friend.name}</span>
                    </div>
                  ))}
                </div>
              ) : (
                // Chat Interface
                <div className="flex flex-col h-96">
                  {/* Messages Area */}
                  <div className="flex-1 p-4 bg-gray-50 overflow-y-auto">
                    <div className="text-center text-gray-500 py-8">
                      <MessageCircle className="w-12 h-12 mx-auto mb-2" />
                      <p>Bắt đầu trò chuyện</p>
                    </div>
                  </div>
                  
                  {/* Input Area */}
                  <div className="border-t p-4">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder="Nhập tin nhắn..."
                        className="flex-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            sendMessage()
                          }
                        }}
                      />
                      <Button
                        onClick={sendMessage}
                        disabled={!message.trim()}
                        className="bg-blue-500 hover:bg-blue-600"
                      >
                        <Send className="w-4 h-4" />
                      </Button>
                    </div>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={backToFriends}
                      >
                        <Users className="w-4 h-4 mr-1" />
                        Danh sách
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}