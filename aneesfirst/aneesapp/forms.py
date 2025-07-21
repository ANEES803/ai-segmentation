from django import forms
from .models import PaintTest

class PaintTestForm(forms.ModelForm):
    """
    Form for uploading room images and specifying paint test parameters.
    """
    
    class Meta:
        model = PaintTest
        fields = ['original_image', 'clicked_x', 'clicked_y', 'color']
        widgets = {
            'original_image': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control',
                'required': True
            }),
            'clicked_x': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'X coordinate (will be set by clicking on image)',
                'readonly': True
            }),
            'clicked_y': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Y coordinate (will be set by clicking on image)',
                'readonly': True
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control',
                'value': '#ff0000'  # Default to red
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels
        self.fields['original_image'].label = 'Upload Room Image'
        self.fields['clicked_x'].label = 'X Coordinate'
        self.fields['clicked_y'].label = 'Y Coordinate'
        self.fields['color'].label = 'Paint Color'
        
        # Set help text
        self.fields['original_image'].help_text = 'Upload a clear image of the room interior'
        self.fields['clicked_x'].help_text = 'Click on the image to set coordinates'
        self.fields['clicked_y'].help_text = 'Click on the image to set coordinates'
        self.fields['color'].help_text = 'Choose the paint color to apply'
        
        # Make coordinates optional (they'll be set by JavaScript)
        self.fields['clicked_x'].required = False
        self.fields['clicked_y'].required = False
    
    def clean_original_image(self):
        """
        Validate the uploaded image file.
        """
        image = self.cleaned_data.get('original_image')
        
        if image:
            # Check file size (limit to 10MB)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError('Image file too large. Please upload an image smaller than 10MB.')
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 'image/tiff']
            if image.content_type not in allowed_types:
                raise forms.ValidationError('Invalid image format. Please upload a JPEG, PNG, BMP, or TIFF image.')
        
        return image
    
    def clean_color(self):
        """
        Validate the color hex code.
        """
        color = self.cleaned_data.get('color')
        
        if color:
            # Ensure it starts with #
            if not color.startswith('#'):
                color = '#' + color
            
            # Validate hex format
            if len(color) != 7:
                raise forms.ValidationError('Invalid color format. Please use a valid hex color code.')
            
            try:
                int(color[1:], 16)  # Try to convert hex to int
            except ValueError:
                raise forms.ValidationError('Invalid color format. Please use a valid hex color code.')
        
        return color
    
    def clean(self):
        """
        Perform cross-field validation.
        """
        cleaned_data = super().clean()
        clicked_x = cleaned_data.get('clicked_x')
        clicked_y = cleaned_data.get('clicked_y')
        
        # If coordinates are provided, ensure both are present
        if (clicked_x is not None and clicked_y is None) or (clicked_x is None and clicked_y is not None):
            raise forms.ValidationError('Both X and Y coordinates must be provided.')
        
        # Ensure coordinates are non-negative
        if clicked_x is not None and clicked_x < 0:
            raise forms.ValidationError('X coordinate must be non-negative.')
        
        if clicked_y is not None and clicked_y < 0:
            raise forms.ValidationError('Y coordinate must be non-negative.')
        
        return cleaned_data

