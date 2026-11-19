"""Readable standalone PDF export of the complete Markdown research report."""
import argparse,os,re,tempfile,textwrap
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'llm-astar-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

def clean(s):
    s=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',s)
    return s.replace('**','').replace('`','')
def main():
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    lines=a.report.read_text().splitlines();page=0;fig=None;y=0
    with PdfPages(a.output) as pdf:
        def fresh():
            nonlocal fig,y,page
            if fig is not None:pdf.savefig(fig);plt.close(fig)
            page+=1;fig=plt.figure(figsize=(8.27,11.69));y=.93
            fig.text(.075,.965,'LLM-A* · Research Session 6 · 19 November 2026',fontsize=8,color='#555555')
            fig.text(.075,.035,f'{page}    Full text and reproducible data: REPORT.md / session6 README.md',fontsize=7,color='#555555')
        def emit(s,size=9.2,bold=False,mono=False):
            nonlocal y
            step=size/72/11.69*1.47
            if y-step<.065:fresh()
            fig.text(.075,y,s,fontsize=size,fontweight='bold' if bold else 'normal',family='monospace' if mono else 'sans-serif',va='top');y-=step
        fresh();i=0;code=False
        while i<len(lines):
            s=lines[i]
            if s.startswith('```'):code=not code;i+=1;continue
            if s.startswith('|'):
                table=[]
                while i<len(lines) and lines[i].startswith('|'):
                    cells=[clean(x.strip()) for x in lines[i].strip('|').split('|')]
                    if not all(re.fullmatch(r':?-+:?',x) for x in cells):table.append(cells)
                    i+=1
                n=len(table[0]);widths=[.29]+[.71/(n-1)]*(n-1)
                if n<=4:widths=[.43]+[.57/(n-1)]*(n-1)
                wrapped=[[textwrap.fill(c,max(7,int(w*125))) for c,w in zip(row,widths)] for row in table]
                maxrows=[max(c.count('\n')+1 for c in row) for row in wrapped]
                heights=[max(.025,m*.0115+.009) for m in maxrows];height=sum(heights)+.012
                if y-height<.065:fresh()
                ax=fig.add_axes([.075,y-height,.85,height]);ax.axis('off')
                t=ax.table(cellText=wrapped[1:],colLabels=wrapped[0],colWidths=widths,cellLoc='left',loc='upper left',bbox=[0,0,1,1]);t.auto_set_font_size(False);t.set_fontsize(6.8)
                for (r,c),cell in t.get_celld().items():
                    cell.set_height(heights[r]/height);cell.set_edgecolor('#cccccc');cell.set_linewidth(.4)
                    if r==0:cell.set_facecolor('#e7eef5');cell.set_text_props(weight='bold')
                    elif r%2==0:cell.set_facecolor('#f6f7f8')
                y-=height+.016;continue
            if not s.strip():y-=.008;i+=1;continue
            if s.startswith('#'):
                level=len(s)-len(s.lstrip('#'));size=16 if level==1 else 11.3
                if y<.16:fresh()
                y-=.008
                for line in textwrap.wrap(clean(s.lstrip('#').strip()),width=70 if level==1 else 95):emit(line,size,True)
                y-=.004;i+=1;continue
            if code:
                for line in textwrap.wrap(s,width=106,replace_whitespace=False,drop_whitespace=False):emit(line,7.1,mono=True)
                i+=1;continue
            paragraph=s;i+=1
            while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','- ')):
                paragraph+=' '+lines[i];i+=1
            for line in textwrap.wrap(clean(paragraph),width=108):emit(line)
        if fig is not None:pdf.savefig(fig);plt.close(fig)
    print('Exported complete report PDF pages:',page)
if __name__=='__main__':main()
