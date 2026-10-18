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

#include "testlib.h"
// Performance anchor: 60 points; logarithmic credit above it.
static double reference_score(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6*r : 0.6 + 0.02*std::log(r);
}

#include <cassert>
using namespace std;
int q[1100];
int query_count = 0, R, H, get_count = 0;
constexpr int query_limit=75, max_position=1000;
int vis[1100],wait_ans[1100];

double cal_score(int rmax){
    double score=0.0;
    if(rmax<=30) score=-1.0*20/3*rmax+1.0*820/3;
    else if(30<rmax&&rmax<=35) score=-1.0*4*rmax+1.0*580/3;
    else if(35<rmax&&rmax<=40) score=-1.0*8/3*rmax+1.0*440/3;
    else if(40<rmax&&rmax<=60) score=-1.0*4/3*rmax+1.0*280/3;
    else if(60<rmax&&rmax<=75) score=1.0*40/3;
    return score/100;
}

bool valid_pos(int x){
    return 1<=x&&x<=max_position;
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);
    R=inf.readInt(),H=inf.readInt();
    int ans_a=ans.readInt(),ans_b=ans.readInt();
    if(ans_a>ans_b) swap(ans_a, ans_b);
    assert(valid_pos(ans_a) && valid_pos(ans_b));

    println(R,H);
    while(true){
        char ch=ouf.readChar();
        while(ch!='!' && ch!='?' && ch!= '@'){
            ch=ouf.readChar();
        }
        if (ch=='?'){
            query_count++;
            if(query_count>query_limit) quitf(_wa, "Too many sends");
            int len=ouf.readInt(),flag=0;
            if(len<0) quitf(_wa, "Invalid length");
            for(int i=1;i<=len;i++){
                q[i]=ouf.readInt();
                if(!valid_pos(q[i])) quitf(_wa, "Invalid position");
                if(vis[q[i]]==query_count) quitf(_wa, "Repeat position");
                vis[q[i]]=query_count;
                if(q[i]==ans_a || q[i]==ans_b) flag=1;
            }
            wait_ans[++wait_ans[0]]=flag;
        }
        else if (ch=='@'){
            get_count++;
            if (get_count > H) quitf(_wa, "Too many gets");
            println(wait_ans,wait_ans+wait_ans[0]+1);
            wait_ans[0]=0;
        }
        else{
            int a=ouf.readInt(),b=ouf.readInt();
            if(a>b) swap(a,b);
            if(a!=ans_a || b!=ans_b) quitf(_wa, "wrong guess (%d, %d), should be (%d, %d)",a,b,ans_a,ans_b);
            break;
        }
    }
    double score_ratio = reference_score(cal_score(query_count));
    score_ratio = natural_log_score(100.0 * score_ratio, query_count, 26.0L, true) / 100.0;
    double unbounded_ratio = score_ratio;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", (long long)(score_ratio*100), score_ratio, unbounded_ratio);
    return 0;
}
