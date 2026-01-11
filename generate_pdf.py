"""
Generate Arabic PDF using WeasyPrint (better Arabic support)
Install: pip install weasyprint
"""

from weasyprint import HTML, CSS
import os


def generate_arabic_math_pdf():
    """Generate PDF from HTML with proper Arabic support"""
    
    html_content = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;700&display=swap');
        
        body {
            font-family: 'Noto Sans Arabic', Arial, sans-serif;
            direction: rtl;
            text-align: right;
            line-height: 1.8;
            margin: 2cm;
            font-size: 12pt;
        }
        
        h1 {
            color: #1a5490;
            font-size: 20pt;
            text-align: center;
            margin-bottom: 1cm;
            font-weight: bold;
        }
        
        h2 {
            color: #2c5282;
            font-size: 16pt;
            margin-top: 1cm;
            margin-bottom: 0.5cm;
            font-weight: bold;
        }
        
        h3 {
            color: #2d3748;
            font-size: 14pt;
            margin-top: 0.5cm;
            margin-bottom: 0.3cm;
            font-weight: bold;
        }
        
        .header {
            text-align: right;
            margin-bottom: 1cm;
        }
        
        ul {
            margin-right: 1cm;
        }
        
        li {
            margin-bottom: 0.3cm;
        }
        
        .duration {
            font-weight: bold;
            color: #555;
        }
    </style>
</head>
<body>
    <div class="header">
        <p>الجمهورية الجزائرية الديمقراطية الشعبية</p>
        <p>وزارة التربية الوطنية</p>
    </div>
    
    <h1>البرنامج السنوي لمادة الرياضيات</h1>
    <h3 style="text-align: center;">السنة الثالثة ثانوي - شعبة العلوم التجريبية</h3>
    <p style="text-align: center;">السنة الدراسية 2024-2025</p>
    
    <h2>المقدمة</h2>
    <p>
        يهدف هذا البرنامج إلى تمكين تلاميذ السنة الثالثة ثانوي من اكتساب المفاهيم الرياضية الأساسية 
        وتطوير قدراتهم على التفكير المنطقي والاستدلال الرياضي. يشمل البرنامج عدة محاور أساسية تغطي 
        مختلف فروع الرياضيات بما يتناسب مع متطلبات شعبة العلوم التجريبية والتحضير لامتحان البكالوريا.
    </p>
    
    <h2>الفصل الأول (سبتمبر - ديسمبر)</h2>
    
    <h3>الوحدة الأولى: الدوال العددية</h3>
    <ul>
        <li>دراسة الدوال وتمثيلها البياني</li>
        <li>النهايات والاستمرارية</li>
        <li>الاشتقاقية وتطبيقاتها</li>
        <li>دراسة تغيرات الدوال والتمثيل البياني</li>
    </ul>
    <p class="duration">المدة الزمنية: 5 أسابيع (20 ساعة)</p>
    
    <h3>الوحدة الثانية: الدوال الأسية واللوغاريتمية</h3>
    <ul>
        <li>تعريف الدالة الأسية وخصائصها</li>
        <li>الدالة اللوغاريتمية النيبيرية</li>
        <li>المعادلات والمتراجحات الأسية واللوغاريتمية</li>
        <li>التطبيقات في العلوم الطبيعية والفيزيائية</li>
    </ul>
    <p class="duration">المدة الزمنية: 4 أسابيع (16 ساعة)</p>
    
    <h3>الوحدة الثالثة: المتتاليات العددية</h3>
    <ul>
        <li>تعريف المتتالية ودراسة سلوكها</li>
        <li>المتتاليات الحسابية والهندسية</li>
        <li>النهايات والمتتاليات المتقاربة</li>
        <li>الاستدلال بالتراجع</li>
    </ul>
    <p class="duration">المدة الزمنية: 3 أسابيع (12 ساعة)</p>
    
    <h2>الفصل الثاني (يناير - مارس)</h2>
    
    <h3>الوحدة الرابعة: الحساب التكاملي</h3>
    <ul>
        <li>التكامل غير المحدود والدوال الأصلية</li>
        <li>التكامل المحدود وخصائصه</li>
        <li>حساب المساحات والحجوم</li>
        <li>التكامل بالتجزئة والتكامل بالتعويض</li>
    </ul>
    <p class="duration">المدة الزمنية: 5 أسابيع (20 ساعة)</p>
    
    <h3>الوحدة الخامسة: الأعداد المركبة</h3>
    <ul>
        <li>مجموعة الأعداد المركبة والعمليات عليها</li>
        <li>الشكل الجبري والشكل المثلثي</li>
        <li>حل المعادلات في مجموعة الأعداد المركبة</li>
        <li>التطبيقات الهندسية للأعداد المركبة</li>
    </ul>
    <p class="duration">المدة الزمنية: 4 أسابيع (16 ساعة)</p>
    
    <h3>الوحدة السادسة: الهندسة في الفضاء</h3>
    <ul>
        <li>المستقيمات والمستويات في الفضاء</li>
        <li>الأشعة والإحداثيات في الفضاء</li>
        <li>الجداء السلمي في الفضاء</li>
        <li>المعادلات الديكارتية والوسيطية</li>
    </ul>
    <p class="duration">المدة الزمنية: 3 أسابيع (12 ساعة)</p>
    
    <div style="page-break-before: always;"></div>
    
    <h2>الفصل الثالث (أبريل - يونيو)</h2>
    
    <h3>الوحدة السابعة: الاحتمالات</h3>
    <ul>
        <li>مفاهيم أساسية في الاحتمالات</li>
        <li>الاحتمال الشرطي والاستقلالية</li>
        <li>المتغيرات العشوائية المنفصلة</li>
        <li>القانون ذو الحدين والتوزيع الطبيعي</li>
    </ul>
    <p class="duration">المدة الزمنية: 4 أسابيع (16 ساعة)</p>
    
    <h3>الوحدة الثامنة: المعادلات التفاضلية</h3>
    <ul>
        <li>تعريف المعادلات التفاضلية من الرتبة الأولى</li>
        <li>حل المعادلات التفاضلية من الشكل y' = ay + b</li>
        <li>المعادلات التفاضلية من الرتبة الثانية</li>
        <li>التطبيقات في الفيزياء والبيولوجيا</li>
    </ul>
    <p class="duration">المدة الزمنية: 3 أسابيع (12 ساعة)</p>
    
    <h3>فترة المراجعة والتحضير للبكالوريا</h3>
    <ul>
        <li>مراجعة شاملة لجميع الوحدات</li>
        <li>حل نماذج امتحانات البكالوريا السابقة</li>
        <li>تدريبات مكثفة على حل المسائل</li>
        <li>تقنيات الامتحان وإدارة الوقت</li>
    </ul>
    <p class="duration">المدة الزمنية: 4 أسابيع (16 ساعة)</p>
    
    <h2>الأهداف العامة للبرنامج</h2>
    <ul>
        <li>تمكين التلاميذ من المفاهيم الرياضية الأساسية اللازمة للتعليم العالي</li>
        <li>تنمية القدرة على التفكير المنطقي والاستدلال الرياضي السليم</li>
        <li>تطوير مهارات حل المشكلات والتحليل الرياضي</li>
        <li>ربط الرياضيات بالمواد العلمية الأخرى وبالحياة اليومية</li>
        <li>التحضير الجيد لامتحان شهادة البكالوريا</li>
    </ul>
    
    <h2>المنهجية البيداغوجية</h2>
    <p>
        يعتمد تدريس البرنامج على المقاربة بالكفاءات التي تجعل التلميذ محور العملية التعليمية. 
        يتم التركيز على الأنشطة التطبيقية وحل المسائل المتنوعة مع استخدام الوسائل التكنولوجية 
        الحديثة عند الحاجة. كما يتم التنويع في طرق التقويم بين الفروض والاختبارات والأعمال التطبيقية 
        لضمان تقييم شامل لمستوى التلاميذ.
    </p>
    
    <h2>التقويم</h2>
    <ul>
        <li>فرضان محروسان في كل فصل دراسي</li>
        <li>اختبار في نهاية كل فصل</li>
        <li>واجبات منزلية منتظمة</li>
        <li>مشاركة فعالة في القسم</li>
        <li>اختبارات تجريبية للبكالوريا في الفصل الثالث</li>
    </ul>
    
    <p style="margin-top: 2cm;">
        <strong>إعداد:</strong> قسم الرياضيات<br>
        <strong>تاريخ الإعداد:</strong> سبتمبر 2024
    </p>
</body>
</html>
"""
    
    # Generate PDF
    output_file = "برنامج_الرياضيات_3AS_صحيح.pdf"
    HTML(string=html_content).write_pdf(output_file)
    
    print(f"✅ Generated: {output_file}")
    print("This PDF has properly encoded Arabic text that will work with Docling!")
    return output_file


if __name__ == "__main__":
    print("=" * 60)
    print("Generating Arabic PDF with WeasyPrint (proper Arabic support)")
    print("=" * 60)
    
    try:
        generate_arabic_math_pdf()
        print("\n✅ Success! Now test this PDF with your API")
        print("The text layer will be properly encoded and sections will be detected!")
    except ImportError:
        print("\n❌ Error: WeasyPrint not installed")
        print("Install it with: pip install weasyprint")
        print("Note: On Linux you may also need: sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0")