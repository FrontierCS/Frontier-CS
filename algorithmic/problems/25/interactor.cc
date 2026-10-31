#include <cmath>
#include <algorithm>

// Natural-log calibration above the previous 60-point threshold.
// Keep validation and low scores; an exact zero minimization cost earns 100.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0 || !(value > 0.0L) || !(anchor > 0.0L))
        return old_points;
    const long double delta = minimize ? std::log(anchor) - std::log(value)
                                       : std::log(value) - std::log(anchor);
    return (double)std::min(100.0L, 60.0L + delta);
}

#include "testlib.h"
#include <vector>

// Reference calibration: 60 points at r=1, logarithmic rewards above it.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

namespace {
    constexpr int MAX_N = 2000 + 10, QUERY_LIM = 3500;
    int cnt_query,best_score;
    int co[MAX_N], m, n, ans_status;
    bool vis[MAX_N];
    std::vector<int> v[MAX_N];
    int solve(){
        int cnt=0;
        for(int i=1;i<=n;i++)
        if(!co[i]){
            for(int j=0;j<v[i].size();j++)
            if(co[v[i][j]]){
                cnt++;
                break;
            }
        }
        //if(n<=10) std::cerr<<cnt<<std::endl;
        return cnt;
    }
    void dfs(int x){
        vis[x]=true;
        for(int i=0;i<v[x].size();i++){
            if(!vis[v[x][i]])
                dfs(v[x][i]);
        }
    }

}  // namespace
double work(){
    n=inf.readInt();
    m=ans.readInt();
    for(int i=0;i<=n;i++) v[i].clear(),vis[i]=0,co[i]=0;
    cnt_query=0;
    for(int i=1,x,y;i<=m;i++){
        x=ans.readInt();
        y=ans.readInt();
        v[x].push_back(y);
        v[y].push_back(x);
    }
    best_score=n*std::max(1,(int)log2(n));
    dfs(1),ans_status=1;
    for(int i=1;i<=n;i++){
        if(!vis[i]){
            ans_status=0;
            break;
        }
    }
    // for (int i = 1; i <= n; i++) {
    //     std::cerr<<p[i]<<" ";
    // }
    // std::cerr<<std::endl;
    println(n);
    std::string op;
    while(true){
        cnt_query++;
        if(cnt_query>QUERY_LIM) quitf(_wa, "Too many queries");
        op=ouf.readString();
        if(op[0]=='?'){
            if(op.length()<n+2) quitf(_wa, "Invalid query,%d",op.length());
            //if(n<=10) std::cerr<<op<<std::endl;
            for(int i=2;i<n+2;i++)
            {
                if(op[i]=='0') co[i-1]=0;
                else if(op[i]=='1') co[i-1]=1;
                else quitf(_wa, "Invalid status");
            }
            println(solve());
        }
        else if(op[0]=='!'){
            if(op.length()<3) quitf(_wa, "Invalid answer,%d",op.length());
            int out=op[2]-'0';
            if(out!=ans_status) quitf(_wa, "Wrong judgement:%d",out);
            break;
        }
        else quitf(_wa, "Invalid query:%s",op.c_str());
    }
    double score=std::max(0.0,1.0*(QUERY_LIM-cnt_query)/(QUERY_LIM-best_score));
    return natural_log_score(100.0 * calibrated(score), cnt_query, best_score, true) / 100.0;
}
int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);
    int T=inf.readInt();
    println(T);
    double sum=0.0,sum_unbounded=0.0,sub_score,tot=T;
    while(T){
        T--;
        sub_score=work();
        sum+=sub_score;
        sum_unbounded+=sub_score;
    }
    double score_ratio=sum/tot;
    double unbounded_ratio=sum_unbounded/tot;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", (long long)(score_ratio*100), score_ratio, unbounded_ratio);
    return 0;
}
