#include <cmath>
#include <algorithm>

// Scores are in points here. Preserve the previous lower band, and compare
// the original objective with its 60-point anchor using the natural logarithm.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0) return old_points;
    // A zero reference or a flat legacy score has no positive logarithmic anchor.
    if (!(value > 0.0L) || !(anchor > 0.0L)) return old_points;
    const long double gain = minimize ? std::log(anchor) - std::log(value)
                                      : std::log(value) - std::log(anchor);
    return static_cast<double>(std::min(100.0L, 60.0L + gain));
}


// Legacy base ratio, retained only to decide and preserve the lower band.
static double penalized(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <cassert>

struct node{
    int id, o[2];
    bool sameo(){return o[0]==o[1];}
};
namespace {

    int query_count = 0, query_limit = 0, guess_count = 0;
    int ans_id,n,cnt_f,cnt_t;
    std::vector<node> v,vf,vt;

    void determin_ans(){
        if(ans_id) return ;
        bool fl=1;
        for(int i=1;i<v.size();i++){
            if(v[i].id!=v[0].id){
                fl=0;
                break;
            }
        }
        if(fl) ans_id=v[0].id;
    }

    std::vector<node> work(int out, int &cnt, int l, int r){
        std::vector<node> res;
        res.clear();
        cnt=0;
        for(int i=0,op,x;i<v.size();i++){
            node t=v[i];
            int value=((l<=t.id)&&(t.id<=r))?r-l:r-l+1;
            if(value==out) op=1;
            else op=0;
            if(t.o[0]==op && t.o[1]==op) continue;
            t.o[0]=t.o[1], t.o[1]=op;
            res.push_back(t);
            if(t.sameo()) cnt++;
        }
        return res;
    }
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);
    int T=inf.readInt(),max_query_count=0;
    double score_ratio=-1;
    double log_score_ratio = 1.0;

    println(T);
    while(T){
        T--;
        n=inf.readInt();
        println(n);

        query_limit=ans.readInt();

        v.clear(),vf.clear(),vt.clear();
        for(int i=1;i<=n;i++){
            node t;
            t.id=i;
            for(int i1=0;i1<2;i1++) for(int i2=0;i2<2;i2++){
                t.o[0]=i1;
                t.o[1]=i2;
                v.push_back(t);
            }
        }
        query_count=guess_count=ans_id=0;

        bool fl=false;
        while(true){
            char ch=ouf.readChar();
            while(ch!='#' && ch!='!' && ch!='?'){
                ch=ouf.readChar();
            }
            if (ch=='?'){
                query_count++;
                if(query_count>query_limit) quitf(_wa, "Too many queries");
                int l=ouf.readInt();
                int r=ouf.readInt();
                if(!(1<=l && l<=r && r<=n)) quitf(_wa, "Invalid l or r");

                vf=work(r-l,cnt_f,l,r);
                vt=work(r-l+1,cnt_t,l,r);
                int opt=r-l;
                if(vf.size()>vt.size()) v=vf;
                else if(vt.size()>vf.size()) v=vt,opt+=1;
                else{
                    if(cnt_f<cnt_t) v=vf;
                    else v=vt,opt+=1;
                }
                println(opt);
                determin_ans();
            }else if (ch=='!'){
                guess_count++;
                if(guess_count>2) quitf(_wa, "Too many guesses");
                int gue=ouf.readInt();
                if(!(1<=gue && gue<=n)) quitf(_wa, "Invalid guess");
                if (ans_id){
                    if(gue==ans_id) fl=1, println(1);
                    else println(0);
                    continue ;
                }
                println(0);
                for(int i=0;i<v.size();i++){
                    if(v[i].id==gue){
                        std::swap(v[i],v.back());
                        v.pop_back();
                        i--;
                    }
                }
                determin_ans();
            }else{
                if (fl==0) quitf(_wa, "No correct guess");
                if(score_ratio < 0) score_ratio = std::max(0.0,1.0*(query_limit-query_count)/(query_limit - 1));
                else score_ratio = std::min(score_ratio, std::max(0.0,1.0*(query_limit-query_count)/(query_limit - 1)));
                max_query_count=std::max(max_query_count, query_count);
    const double case_points = 100.0 * std::max(0.0, std::min(1.0, 1.0*(query_limit-query_count)/(query_limit-1)));
    log_score_ratio = std::min(log_score_ratio, natural_log_score(case_points, query_count, 0.4L*query_limit+0.6L, true)/100.0);
                break;
            }
        }
    }
    double unbounded_ratio = score_ratio;
    score_ratio = std::min(1.0, score_ratio);
    score_ratio=log_score_ratio;
    unbounded_ratio=score_ratio;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", (long long)(score_ratio*100), score_ratio, unbounded_ratio);
    return 0;
}
