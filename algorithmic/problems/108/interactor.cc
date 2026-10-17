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

int p[5100],q[5100];
int query_count = 0;
constexpr int query_limit=30000, full_score=1;
bool vis[5100];

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);
    int n=inf.readInt(),m=inf.readInt();
    for(int i=1;i<n;i++){
        p[i]=ans.readInt(),q[i]=p[i];
        if(p[i]<0||p[i]>=n*m) quitf(_wa, "Invalid input");
    }
    
    println(n,m);
    while(true){
        char ch=ouf.readChar();
        while(ch!='!' && ch!='?'){
            ch=ouf.readChar();
        }
        if (ch=='?'){
            query_count++;
            if(query_count>query_limit) quitf(_wa, "Too many queries");
            int x=ouf.readInt();
            int d=ouf.readInt();
            if(!(x>=0 && x<n)) quitf(_wa, "Invalid x");
            if(d==1){
                q[x]++;
                if(q[x]>=n*m) q[x]-=n*m;
            }
            else if(d==-1){
                q[x]--;
                if(q[x]<0) q[x]+=n*m;
            }
            else quitf(_wa, "Invalid d");

            for(int j=0;j<n;j++){
                for(int now=q[j],k=0;k<m;k++,now++){
                    now%=n*m;
                    vis[now]=true;
                }
            }
            int q_ans=0;
            for(int i=0;i<n*m;i++){
                if(vis[i]) vis[i]=0;
                else q_ans++;
            }
            println(q_ans);
        }
        else{
            for(int i=1;i<n;i++){
                int gue=ouf.readInt()+q[0];
                gue%=n*m;
                if(gue<0) gue+=n*m;
                if(gue!=q[i]) quitf(_wa, "wrong guess %d, %d and %d",i, q[i], gue);
            }
            break;
        }
    }
    double score=full_score*(1.0*(query_limit-query_count)/query_limit);
    score=penalized(score);
    score = natural_log_score(100.0 * score, query_count, 12000.0L, true) / 100.0;
    quitp(score, "qurey count: %d, Ratio: %.12f",query_count, score);
    return 0;
}
