# Check what we currently have
ls -la public/

# Create simple colored square icons using your existing logo.png
# If logo.png exists, resize it; otherwise create simple colored squares

if [ -f "public/logo.png" ]; then
    echo "✅ Found logo.png - will use as base for PWA icons"
    cp public/logo.png public/icon-192.png
    cp public/logo.png public/icon-512.png
else
    echo "⚠️  No logo.png found - creating simple colored placeholder icons"
    
    # Create simple HTML-based icons (fallback method)
    # Create a simple 192x192 colored square
    echo '<svg width="192" height="192" xmlns="http://www.w3.org/2000/svg">
  <rect width="192" height="192" fill="#3B82F6"/>
  <text x="50%" y="50%" font-family="Arial" font-size="72" fill="white" text-anchor="middle" dy="0.35em">H</text>
</svg>' > public/icon-192.svg
    
    # Create a simple 512x512 colored square
    echo '<svg width="512" height="512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" fill="#3B82F6"/>
  <text x="50%" y="50%" font-family="Arial" font-size="200" fill="white" text-anchor="middle" dy="0.35em">H</text>
</svg>' > public/icon-512.svg
    
    echo "✅ Created simple SVG icons as placeholders"
fi
