#!/usr/bin/env python3
"""
Author: Ben Knisley [benknisley@gmail.com]
Date: May 8, 2018
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GObject
import random


class Tetromino:
    """
    Class that represents the current falling piece.

    Abstracts a mobile collection of block elements collectively known as a 
    piece. The piece has an absolute coordinate on the playing field. Each 
    block element making up the piece is defined by a coordinate relative 
    to the absolute coordinates of a collective piece. The piece is created 
    using a list of relative coordinates.
    """

    def __init__(self, parent, blocks=None):
        """
        Constructs a Tetromino Object.
        
        Setups absolute x and y coords, stores a list of relative coordinates,
        and a rotation variable.
        """
        self.parent = parent
        self.x = int(parent.block_width / 2) ## x coord of base block element
        self.y = parent.block_height

        ## Setup rotate variable
        self.rotate = 0

        if blocks:
            self.block_elements = blocks ## Relative coords
        else:
            self.block_elements = [(-1,0),(0, 0),(1,0),(2,0)] ## Relative coord
    
    def get_block_coords(self):
        """
        Computes a list of absolute coordinates for each block element.
        """
        ## Create list to store coordinates in
        block_coords = []

        ## Loop through rel coords of each block element
        for x, y in self.block_elements:
            
            ## Calculate new coordinates based of rotation
            if self.rotate == 1:
                x, y = -y, x
            elif self.rotate == 2:
                x, y = -x, -y
            elif self.rotate == 3:
                x,y = y,-x 
            
            ## Calculate absolute coords
            abs_x, abs_y = int(self.x+x), int(self.y+y)

            ## Load abs coords into block_coords
            block_coords.append( (abs_x, abs_y) )
        
        ## Return loaded block_coords list
        return block_coords

    def change_valid(self, dx=0, dy=0, dr=0):
        """
        Checks if a proposed change would be valid. Collision Detection.
        """
        ## Create list to hold now coords
        new_coords = []

        ## Calculate new rotation value  
        new_r = (self.rotate+dr)%4

        ## Get rel coords for each block element
        for rel_x, rel_y in self.block_elements:
            ## rotate rel coords using new rotations value
            if new_r == 1:
                rel_x, rel_y = -rel_y, rel_x
            elif new_r == 2:
                rel_x, rel_y = -rel_x, -rel_y
            elif new_r == 3:
                rel_x, rel_y = rel_y, -rel_x 

            ## Calculate new abs coords
            new_x = int(self.x + rel_x + dx)
            new_y = int(self.y + rel_y + dy)
            
            ## Append new coords to new_coords list
            new_coords.append((new_x, new_y))

        ## Check for border collisions
        max_x = self.parent.block_width - 1
        border_collision = any((
            ## Wall collision checks
            any([x < 0 for x,y in new_coords]),
            any([x > max_x for x,y in new_coords]),
            ## Floor collision
            any([y < 0 for x,y in new_coords]) 
        ))

        ## If border collision, return false
        if border_collision:
            return False

        ## Check for collisions with crumble
        crumble = self.parent.crumble
        block_collision = any([crumble[x, y] for x,y in new_coords])

        ## If block collision, return false
        if block_collision:
            return False

        ## If no collision return True
        return True

    def move_down(self):
        """ Moves piece down one row """
        self.y -= 1

    def rotate_right(self):
        """ Rotates piece clockwise """
        if self.change_valid(dr=1):
            self.rotate = (self.rotate+1)%4
        
    def rotate_left(self):
        """ Rotates piece counter clockwise """
        if self.change_valid(dr=-1):
            self.rotate = (self.rotate-1)%4

    def move_right(self):
        """ Moves piece right one column """
        if self.change_valid(dx=1):
            self.x += 1

    def move_left(self):
        """ Moves piece left one column """
        if self.change_valid(dx=-1):
            self.x -= 1

    def draw(self, parent, cr):
        """
        Draws the Tetromino piece onto the parent Tetris widget.
        Calls the parent Tetris objects' draw_block_element method on each
        block in piece. 
        """
        for x, y in self.get_block_coords():
            parent.draw_block_element(cr, x, y)


class Crumble:
    """
    Class to represent and store the blocks that have fallen to the bottom of 
    the playfield. 

    Stores a list of lists of boolean values representing a matrix of blocks.
    """
    def __init__(self, parent, block_width, block_height):
        """
        Sets up a Crumble Matrix object with given block width & height.
        """
        ## Set width and height of playfield
        self.block_height = block_height
        self.block_width = block_width

        ## Create list to hold matrix (list of rows, list of blocks)
        self.matrix = []

        ## Create an empty row with all false values
        self.empty_row = [False] * self.block_width
        
        ## Stack empty rows in matrix 
        for _ in range(block_height):
            self.matrix.append(self.empty_row.copy())
    
    def __repr__(self):
        out_str = ""
        for row in self.matrix[::-1]:
            for cell in row:
                if cell:
                    out_str += 'X'
                else:
                    out_str += '-'
            out_str += '\n'
        return out_str

    def __getitem__(self, key):
        """
        Magic method that sets the value of a single block coordinate.
        """
        x, y = key
        if y >= self.block_height:
            return False
        return self.matrix[y][x]
    
    def __setitem__(self, key, val):
        """
        Magic method that sets the value of a single block coordinate.
        """
        x, y = key
        self.matrix[y][x] = val

    def add_blocks(self, block_list):
        """
        Adds a list of blocks to the crumble, by setting their coordinates to
        True. Does not check if those values are already True. 
        Format for block_list is [(x,y), (x,y), (x,y), ...]
        """
        blocks = block_list.copy() ## Fixes bug??
        for block in block_list:
            x, y = block
            self[x, y] = True

    def remove_row(self, index):
        """
        Removes a row at the given index from the matrix, replacing it with an 
        empty row at the top of the playfield.
        """
        _ = self.matrix.pop(index) ## Delete row
        self.matrix.append(self.empty_row.copy())

    def check(self):
        """
        Checks and processes for two score conditions: one, if there are any 
        completed rows, and removes them. Two, if there are any blocks in the 
        top most row, and calls game over. Returns the number to increase the
        total score by, or a -1 if the game should end.
        """
        ## Loop through each row, storing its index if it is completely full
        full_rows = []
        for i, row in enumerate(self.matrix):
            if all(row):
                full_rows.append(i)
        
        ## Loop through full rows calling remove_row of each
        for row in full_rows:
            self.remove_row(row)
        
        ## Check second top most row for has any blocks, if there, end game
        if any(self.matrix[self.block_height-2]):
            return -1
        
        ## Return number of full rows found
        return len(full_rows)

    def draw(self, parent, cr):
        """
        Draws the crumble blocks.
        Method iterates over all rows and block bool values, and calls
        Tetris.draw_block_element if block exists there.
        """
        for y, row in enumerate(self.matrix):
            for x, cell in enumerate(row):
                if cell:
                    parent.draw_block_element(cr, x, y)


class Tetris(Gtk.DrawingArea):
    def __init__(self):
        Gtk.DrawingArea.__init__(self)

        ## Connect 'draw' signal to draw method
        self.connect("draw", self.draw)

        ## Set block params
        self.block_size = 25 ## The actual pixel size of a block
        self.block_width = 10 ## The number of blocks wide the playfield is
        self.block_height = 40 ## The number of blocks high the playfield is

        ## Set tick interval
        self.tick_time = 200
        
        ## Setup timer placeholders
        self.timer = None
        self.reset_timer = None

        ## Keep Track of score, and game over status
        self.score = 0
        self.game_over = False

        ## Create a Crumble obj and a placeholder for current falling piece
        self.current = None
        self.crumble = Crumble(self, self.block_width, self.block_height)


    """ Game Methods """

    def load_new_piece(self):


        pieces = [
            [(-1,0),(0, 0),(1,0),(2,0)], ## Line piece
            [(1,0),(0,0),(0,-1),(0,-2)], ## L piece
            [(-1,0),(0,0),(0,-1),(0,-2)], ## j piece
            [(0,0),(1, 0),(0,1),(1,1)], ## Square
            [(-1,0),(0, 0),(0,-1),(1,-1)], ## Front Squiggle
            [(-1,-1),(0, -1),(0,0),(1,0)], ## Back Squiggle
            [(0,0),(1, 0),(0,-1),(0,1)] ## Triblock
        ]

        self.end_jump()

        piece = pieces[random.randrange(len(pieces))]

        new_piece = Tetromino(self, piece)

        self.current = new_piece

    def tick(self):

        ## If there is a current piece
        if self.current:
            ## Get Coords of all blocks in current piece
            blocks = self.current.get_block_coords()

            ## Check next row for any block elements in crumble
            if any([self.crumble[b[0], b[1]-1] for b in blocks]):
                ## Add current blocks to crumble
                self.crumble.add_blocks(blocks)
                self.current = None

            else:
                ## Move current piece down one block
                self.current.move_down()

                ## Check if piece has reached the ground 
                if 0 in [b[1] for b in blocks]:
                    self.crumble.add_blocks(blocks)
                    self.current = None
            
            ## Check crumble, and get score adder
            score_plus = self.crumble.check()

            ## If score_plus is -1, game over
            if score_plus == -1:
                self.end_game()
                self.call_redraw()
                return False
            
            ## Else, add score adder to total score
            else:
                 self.score += score_plus
                 self.call_redraw()
                 return True


        ## If there is not a current piece
        else:
            ## load a new one
            self.load_new_piece()
            return True
   
            
        ## Return True to keep timer going
        return True

    """ Game Control Methods """

    def start_game(self):
        ## Create a tick timer object
        if not self.timer:
            self.timer = GObject.timeout_add(self.tick_time, self.tick)
    
    def end_game(self):
        ## Set game over to True
        self.game_over = True

        ## Kill tick timer
        if self.timer:
            GObject.source_remove(self.timer)
            self.timer = None

        ## Kill reset timer
        if self.reset_timer:
            GObject.source_remove(self.reset_timer)
            self.reset_timer = None
        
        ## Redraw 
        self.call_redraw()

    def reset_game(self):
        ## Game Over
        self.end_game()

        ## Clear current piece and crumble
        self.current = None
        self.crumble = Crumble(self, self.block_width, self.block_height)
        
        ## Clear score
        self.score = 0

        ## Set game to not active, and not over
        self.game_over = False

        ## Redraw 
        self.call_redraw()


    """ Piece Control Methods """

    def pause(self):
        if self.timer:
            GObject.source_remove(self.timer)
            self.timer = None
        else:
            self.timer = GObject.timeout_add(self.tick_time, self.tick)

    def left(self):
        if self.timer:
            if self.current:
                self.current.move_left()

    def right(self):
        if self.timer:
            if self.current:
                self.current.move_right()

    def rotate(self):
        if self.timer:
            if self.current:
                self.current.rotate_right()

    def jump(self):
        if self.timer:
            if self.reset_timer:
                GObject.source_remove(self.reset_timer)
            else:
                GObject.source_remove(self.timer)
                self.timer = GObject.timeout_add(int(self.tick_time/10), self.tick)
            ## ...
            self.reset_timer = GObject.timeout_add(self.tick_time*2, self.end_jump)

    def end_jump(self):
        ## If reset timer is set, remove it
        if self.reset_timer:
            GObject.source_remove(self.reset_timer)
        self.reset_timer = None

        ## Reset timer
        GObject.source_remove(self.timer)
        self.timer = GObject.timeout_add(self.tick_time, self.tick)


    """ Drawing Methods """

    def calculate_bounds(self):
        self.floor_height = self.get_allocated_height() - (self.block_height * self.block_size)
        self.floor_pix_y = self.block_height * self.block_size
        self.wall_width = (self.get_allocated_width() - (self.block_width * self.block_size))/2
        self.wall_pix_x = self.wall_width + (self.block_width * self.block_size)

    def draw_block_element(self, cr, x, y):
        """ Draws a block with the given block coord """
        cr.rectangle(
            self.wall_width+x*self.block_size, 
            (self.block_height-y-1)*self.block_size, 
            self.block_size, self.block_size
        )
        
        cr.set_source_rgb(0.2, 0.25, 0.5)
        cr.fill_preserve()

        cr.set_source_rgb(0.8,0.8,0.8)
        cr.set_line_width(self.block_size/10)
        cr.stroke()

    def draw_background(self, cr):
        ## Draw background
        cr.set_source_rgb(0,0,0)
        cr.paint()

        ## Draw Floor
        cr.set_source_rgb(0.2, 0.2, 0.2)
        cr.rectangle(0, self.floor_pix_y, self.get_allocated_width(), self.floor_height)
        cr.fill()
        
        ## Draw walls
        cr.rectangle(0, 0, self.wall_width, self.get_allocated_height())
        cr.fill()
        cr.rectangle(self.wall_pix_x, 0, self.wall_width, self.get_allocated_height())
        cr.fill()

    def draw(self, caller, cr):
        ## Draw background
        self.calculate_bounds()
        self.draw_background(cr)

        ## 
        self.crumble.draw(self, cr)
        
        ## Draw current piece
        if self.current:
            self.current.draw(self, cr)

        ## Draw Score
        cr.set_source_rgb(1,1,1)
        cr.set_font_size(18)
        cr.move_to(20, 30)
        cr.show_text(f"SCORE: {self.score}")

        if self.game_over:
            ## Draw Score
            cr.set_source_rgb(1,0,0)
            cr.set_font_size(40)

            x, y, width, height, dx, dy = cr.text_extents("GAME OVER")
            h = self.get_allocated_height()
            w = self.get_allocated_width()

            cr.move_to((w/2 - width/2), h/2)  
            cr.show_text("GAME OVER")

    def call_redraw(self):
        self.queue_draw()


class GameWindow(Gtk.Window):
    """
    A Gtk window the user sees and interactions with. Contains a single Tetris 
    widget. Handles keypress and sends controls to Tetris widget.
    """
    def __init__(self):
        ## Implement inheritance from Gtk.Window & Gtk.GObject
        Gtk.Window.__init__(self) ## Because it is a window
        GObject.GObject.__init__(self) ## Because we want to use signals

        ## Set self window properties
        self.resize(500, 800)
        self.set_border_width(0)
        self.set_title("TETRIS")

        ## Create widgets
        self.tetris = Tetris()

        ## Connect Signals to handelers
        self.connect("key_press_event", self.keypress_handler)

        ## Create and pack main layout
        layout = Gtk.VBox()
        layout.pack_start(self.tetris, True, True, 0)
        self.add(layout)

        ## Resize self to be desired size of Tetris widget
        self.resize(self.tetris.block_size*self.tetris.block_width, self.tetris.block_size*self.tetris.block_height)

        ## Show all widgets
        self.show_all()

        ## Start the game!
        self.tetris.start_game()

    def keypress_handler(self, caller, event):
        """
        Handles keypresses for window, sending commands to tetris widget.
        """
        ## Handle right arrow key press
        if event.keyval == 65363:
            self.tetris.right()

        ## Handle left arrow key press
        elif event.keyval == 65361:
            self.tetris.left()

        ## Handle up arrow key press
        elif event.keyval == 65362:
            self.tetris.rotate()

        ## Handle down arrow key press
        elif event.keyval == 65364:
            self.tetris.jump()

        ## Handle spacebar or pause key press
        elif event.keyval in (32, 65299): ## Spacebar 
            self.tetris.pause()
        
        ## Call redraw on game
        self.tetris.call_redraw()


class PyTetrisApp(Gtk.Application):
    def __init__(self):
        ## Implement inheritance from Gtk.Application
        Gtk.Application.__init__(self, 
            application_id="com.benknisley.PyTetris", 
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        ## Connect activate signal with on_activate method
        self.connect("activate", self.on_activate)

    def on_activate(self, caller):
        """
        Handles Application "activate" signal. Creates a GameWindow and adds
        it to application.
        """
        self.window = GameWindow()
        self.add_window(self.window)


## Run application if not imported
if __name__ == "__main__":
    ## Create and run a PyTetrisApp instance
    application = PyTetrisApp()
    application.run()

