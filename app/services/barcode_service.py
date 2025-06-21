# app/services/barcode_service.py

"""
Barcode generation service for equipment serial numbers.
"""
import io
import base64
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class BarcodeService:
    """Service for generating barcodes for equipment."""
    
    @staticmethod
    def generate_barcode_image(serial_number, format='PNG'):
        """
        Generate a barcode image for the given serial number.
        
        Args:
            serial_number (str): The serial number to encode
            format (str): Image format (PNG, JPEG, etc.)
            
        Returns:
            bytes: The barcode image as bytes
        """
        try:
            # Create barcode
            code = Code128(serial_number, writer=ImageWriter())
            
            # Generate barcode image in memory
            buffer = io.BytesIO()
            code.write(buffer, options={
                'module_width': 0.3,  # Make bars wider
                'module_height': 8.0,  # Make bars shorter
                'quiet_zone': 3.0,    # Adjust quiet zone
                'font_size': 8,       # Smaller font for shorter barcode
                'text_distance': 3.0, # Adjust text distance
                'background': 'white',
                'foreground': 'black',
            })
            
            # Get image bytes
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating barcode for {serial_number}: {str(e)}")
            raise
    
    @staticmethod
    def generate_barcode_base64(serial_number):
        """
        Generate a barcode image as base64 string for web display.
        
        Args:
            serial_number (str): The serial number to encode
            
        Returns:
            str: Base64 encoded barcode image
        """
        try:
            image_bytes = BarcodeService.generate_barcode_image(serial_number)
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Error generating base64 barcode for {serial_number}: {str(e)}")
            raise
    
    @staticmethod
    def generate_printable_barcode(serial_number, equipment_name=None, department=None):
        """
        Generate a printable barcode with additional information.
        
        Args:
            serial_number (str): The serial number to encode
            equipment_name (str): Optional equipment name
            department (str): Optional department name
            
        Returns:
            bytes: The printable barcode image as bytes
        """
        try:
            # Generate basic barcode
            barcode_bytes = BarcodeService.generate_barcode_image(serial_number)
            
            # Open the barcode image
            barcode_img = Image.open(io.BytesIO(barcode_bytes))
            
            # Create a larger canvas for additional text
            canvas_width = max(barcode_img.width, 400)
            canvas_height = barcode_img.height + 100  # Extra space for text
            
            canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
            
            # Paste barcode in center
            barcode_x = (canvas_width - barcode_img.width) // 2
            canvas.paste(barcode_img, (barcode_x, 20))
            
            # Add text information (this would require PIL font handling)
            # For now, just return the basic barcode
            
            # Convert back to bytes
            output_buffer = io.BytesIO()
            canvas.save(output_buffer, format='PNG')
            output_buffer.seek(0)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating printable barcode for {serial_number}: {str(e)}")
            raise

