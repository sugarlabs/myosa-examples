#! /usr/bin/env python
#
# demoiselle.py Standalone version of DemoiselleActivity.py
# Copyright (C) 2010  James D. Simmons
# Adapted from code in the article "Rapid Game Development In
# Python" by Richard Jones.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

import pygame
import math
import sys

class Demoiselle:
    "This is a simple demonstration of using PyGame \
    sprites and collision detection."
    def __init__(self):
        self.background = pygame.image.load('sky.jpg')
        self.screen = pygame.display.get_surface()
        self.screen.blit(self.background, (0, 0))
        self.clock = pygame.time.Clock()
        self.running = True

        gliders = [
            GliderSprite((200, 200)),
            GliderSprite((800, 200)),
            GliderSprite((200, 600)),
            GliderSprite((800, 600)),
        ]
        self. glider_group = pygame.sprite.RenderPlain(gliders)
        
    def run(self):
        "This method processes PyGame messages"
        rect = self.screen.get_rect()
        airplane = AirplaneSprite('demoiselle.png', rect.center)
        airplane_sprite = pygame.sprite.RenderPlain(airplane)
        
        while self.running:
            self.clock.tick(30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: 
                    self.running = False
                    return
                elif event.type == pygame.VIDEORESIZE:
                    pygame.display.set_mode(event.size,  pygame.RESIZABLE)
                    self.screen.blit(self.background, (0, 0))
                
                if not hasattr(event, 'key'): 
                    continue
                down = event.type == pygame.KEYDOWN
                if event.key == pygame.K_DOWN or \
                    event.key == pygame.K_KP2: 
                    airplane.joystick_back = down * 5
                elif event.key == pygame.K_UP or \
                    event.key == pygame.K_KP8: 
                    airplane.joystick_forward = down * -5
                elif event.key == pygame.K_EQUALS or \
                    event.key == pygame.K_KP_PLUS or \
                    event.key == pygame.K_KP9:
                    airplane.throttle_up = down * 2
                elif event.key == pygame.K_MINUS or \
                    event.key == pygame.K_KP_MINUS or \
                    event.key == pygame.K_KP3: 
                    airplane.throttle_down = down * -2

            self.glider_group.clear(self.screen, self.background)
            airplane_sprite.clear(self.screen, self.background)
            collisions = pygame.sprite.spritecollide(airplane, \
                                                     self.glider_group,  False)
            self.glider_group.update(collisions)
            self.glider_group.draw(self.screen)
            airplane_sprite.update()
            airplane_sprite.draw(self.screen)
            pygame.display.flip()

class AirplaneSprite(pygame.sprite.Sprite):
    "This class represents an airplane, the Demoiselle \
    created by Alberto Santos-Dumont"
    MAX_FORWARD_SPEED = 10
    MIN_FORWARD_SPEED = 1
    ACCELERATION = 2
    TURN_SPEED = 5
    def __init__(self, image, position):
        pygame.sprite.Sprite.__init__(self)
        self.src_image = pygame.image.load(image)
        self.rect = pygame.Rect(self.src_image.get_rect())
        self.position = position
        self.rect.center = self.position
        self.speed = 1
        self.direction = 0
        self.joystick_back = self.joystick_forward = \
            self.throttle_down = self.throttle_up = 0
        
    def update(self):
        "This method redraws the airplane in response\
        to events."
        self.speed += (self.throttle_up + self.throttle_down)
        if self.speed > self.MAX_FORWARD_SPEED:
            self.speed = self.MAX_FORWARD_SPEED
        if self.speed < self.MIN_FORWARD_SPEED:
            self.speed = self.MIN_FORWARD_SPEED
        self.direction += (self.joystick_forward + self.joystick_back)
        x_coord, y_coord = self.position
        rad = self.direction * math.pi / 180
        x_coord += -self.speed * math.cos(rad)
        y_coord += -self.speed * math.sin(rad)
        screen = pygame.display.get_surface()
        if y_coord < 0:
            y_coord = screen.get_height()
            
        if x_coord < 0:
            x_coord = screen.get_width()
            
        if x_coord > screen.get_width():
            x_coord = 0
            
        if y_coord > screen.get_height():
            y_coord = 0
        self.position = (x_coord, y_coord)
        self.image = pygame.transform.rotate(self.src_image, -self.direction)
        self.rect = self.image.get_rect()
        self.rect.center = self.position

class GliderSprite(pygame.sprite.Sprite):
    "This class represents an individual hang glider as developed\
    by Otto Lilienthal."
    def __init__(self, position):
        pygame.sprite.Sprite.__init__(self)
        self.normal = pygame.image.load('glider_normal.png')
        self.rect = pygame.Rect(self.normal.get_rect())
        self.rect.center = position
        self.image = self.normal
        self.hit = pygame.image.load('glider_hit.png')
    def update(self, hit_list):
        "This method redraws the glider when it collides\
        with the airplane and when it is no longer \
        colliding with the airplane."
        if self in hit_list: 
            self.image = self.hit
        else: 
            self.image = self.normal

def main():
    "This function is called when the game is run from the command line"
    pygame.init()
    pygame.display.set_mode((0, 0), pygame.RESIZABLE)
    game = Demoiselle() 
    game.run()
    sys.exit(0)

if __name__ == '__main__':
    main()
