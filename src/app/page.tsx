'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { MessageCircle, UserPlus, Users, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { MessageCircle, UserPlus, Users, Loader2 } from 'lucide-react'
import SimpleChatWidget from '@/components/simple-chat-widget'


interface User {
    id: number
    username: string
    name: string
    avatar: string
}

interface FriendshipStatus {
    user: User
    friendship_status: 'friends' | 'pending' | 'not_friends'
    can_chat: boolean
    can_add_friend: boolean
}

export default function Home() {
    const [users, setUsers] = useState<User[]>([])
    const [friendshipStatuses, setFriendshipStatuses] = useState<{ [key: number]: FriendshipStatus }>({})
    const [loading, setLoading] = useState(true)
    const currentUserId = '1'

    useEffect(() => {
        fetchUsers()
    }, [])

    const fetchUsers = async () => {
        try {
            setLoading(true)
            const mockUsers: User[] = [
                { id: 1, username: 'me_be_1', name: 'Mẹ Bé 1', avatar: '/avatar1.jpg' },
                { id: 2, username: 'me_be_2', name: 'Mẹ Bé 2', avatar: '/avatar2.jpg' },
                { id: 3, username: 'me_be_3', name: 'Mẹ Bé 3', avatar: '/avatar3.jpg' },
                { id: 4, username: 'me_be_4', name: 'Mẹ Bé 4', avatar: '/avatar4.jpg' },
            ]
            setUsers(mockUsers)
            checkAllFriendshipStatuses(mockUsers)
        } catch (error) {
            console.error('Lỗi khi tải danh sách người dùng:', error)
        } finally {
            setLoading(false)
        }
    }

    const checkAllFriendshipStatuses = async (userList: User[]) => {
        try {
            setLoading(true)
            const statuses: { [key: number]: FriendshipStatus } = {}

            for (const user of userList) {
                if (user.id.toString() === currentUserId) continue

                const response = await fetch(`/api/friendship-status?user_id=${user.id}&current_user_id=${currentUserId}`)
                if (response.ok) {
                    const data = await response.json()
                    statuses[user.id] = data
                }
            }

            setFriendshipStatuses(statuses)
        } catch (error) {
            console.error('Lỗi khi kiểm tra trạng thái bạn bè:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleAddFriend = async (userId: number) => {
        try {
            const response = await fetch('/api/friends/request', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    receiver_id: userId,
                    sender_id: parseInt(currentUserId)
                })
            })

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(errorData.error || 'Không thể gửi lời mời kết bạn')
            }

            await checkAllFriendshipStatuses(users)
        } catch (error) {
            console.error('Lỗi khi gửi lời mời kết bạn:', error)
            alert(error instanceof Error ? error.message : 'Đã xảy ra lỗi')
        }
    }

    const handleStartChat = (userId: number) => {
        window.location.href = `/chat?user_id=${userId}`
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
                    <p className="text-gray-600">Đang tải danh sách mẹ bé...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white shadow-sm border-b">
                <div className="max-w-4xl mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-pink-500 rounded-full flex items-center justify-center">
                                <Users className="w-6 h-6 text-white" />
                            </div>
                            <h1 className="text-2xl font-bold text-gray-900">MomConnect</h1>
                        </div>
                        <Badge variant="outline" className="bg-pink-50 text-pink-700 border-pink-200">
                            Kết nối các mẹ bé
                        </Badge>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-4xl mx-auto px-4 py-8">
                <div className="mb-8 text-center">
                    <h2 className="text-3xl font-bold text-gray-900 mb-2">
                        Chào mừng đến với MomConnect! 👋
                    </h2>
                    <p className="text-gray-600">
                        Kết nối và chia sẻ kinh nghiệm với các mẹ bé khác
                    </p>
                </div>

                {/* Users Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {users
                        .filter(user => user.id.toString() !== currentUserId)
                        .map(user => {
                            const status = friendshipStatuses[user.id]

                            return (
                                <Card key={user.id} className="hover:shadow-lg transition-shadow">
                                    <CardHeader className="pb-3">
                                        <div className="flex items-center space-x-3">
                                            <Avatar className="w-12 h-12">
                                                <AvatarImage src={user.avatar} />
                                                <AvatarFallback>
                                                    {user.name.charAt(0)}
                                                </AvatarFallback>
                                            </Avatar>
                                            <div className="flex-1">
                                                <CardTitle className="text-lg">{user.name}</CardTitle>
                                                <p className="text-sm text-gray-600">@{user.username}</p>
                                            </div>
                                        </div>
                                    </CardHeader>

                                    <CardContent className="pt-0">
                                        {/* Status Badge */}
                                        <div className="mb-4">
                                            {status?.friendship_status === 'friends' && (
                                                <Badge variant="default" className="bg-green-100 text-green-800">
                                                    Đã là bạn bè
                                                </Badge>
                                            )}
                                            {status?.friendship_status === 'pending' && (
                                                <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                                                    Đã gửi lời mời kết bạn
                                                </Badge>
                                            )}
                                            {status?.friendship_status === 'not_friends' && (
                                                <Badge variant="outline" className="bg-gray-100 text-gray-800">
                                                    Chưa kết bạn
                                                </Badge>
                                            )}
                                        </div>

                                        {/* Action Buttons */}
                                        <div className="flex space-x-2">
                                            {status?.can_chat && (
                                                <Button
                                                    onClick={() => handleStartChat(user.id)}
                                                    className="flex-1"
                                                    size="sm"
                                                >
                                                    <MessageCircle className="w-4 h-4 mr-2" />
                                                    Nhắn tin
                                                </Button>
                                            )}

                                            {status?.can_add_friend && (
                                                <Button
                                                    onClick={() => handleAddFriend(user.id)}
                                                    variant="outline"
                                                    className="flex-1"
                                                    size="sm"
                                                >
                                                    <UserPlus className="w-4 h-4 mr-2" />
                                                    Kết bạn
                                                </Button>
                                            )}

                                            {status?.friendship_status === 'pending' && (
                                                <Button
                                                    disabled
                                                    variant="outline"
                                                    className="flex-1"
                                                    size="sm"
                                                >
                                                    <UserPlus className="w-4 h-4 mr-2" />
                                                    Đang chờ
                                                </Button>
                                            )}
                                        </div>
                                    </CardContent>
                                </Card>
                            )
                        })}
                </div>
            </main>
            {/* Simple Chat Widget */}
            <SimpleChatWidget />
        </div>
    )
}