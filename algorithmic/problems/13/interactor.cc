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


// Human reference earns 60 points; improvement remains uncapped.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include "testlib.h"
#include <vector>

namespace {
    constexpr int MAX_N = 3000 + 50, T = 3000;
    int cnt_query, full_score,best_score;
    int co[MAX_N][MAX_N], n, dir[8][2]={{0,1},{0,-1},{1,0},{-1,0},{1,1},{-1,-1},{1,-1},{-1,1}};
    double vis[MAX_N];
    struct node{
        int x,y;
        bool valid(){
            return (x>=1)&&(x<=T)&&(y>=1)&&(y<=T);
        }
        bool validr(){
            return (x>=1)&&(y>=1)&&co[x][y]==0;
        }

        int dis(node b){
            return abs(x-b.x)+abs(y-b.y);
        }
    }s;
    node n0={0,0};
    std::vector<node> v,bl;
    /*
    node ran(){
        int i=(int)rnd.next()%(int)(v.size());
        return v[i];
    }
    */
    node nest(){
        int id=0;
        for(int i=0;i<v.size();i++){
            vis[i]=0;
            for(int j=0;j<bl.size();j++){
                vis[i]+=1.0/v[i].dis(bl[j]);
            }
            if(vis[i]<vis[id]) id=i;
        }
        return v[id];
    }
    node solve(node t){
        if(!co[t.x][t.y]) bl.push_back(t);
        co[t.x][t.y]=1;
        node ny;
        v.clear();
        for(int i=0;i<8;i++){
            ny.x=s.x+dir[i][0];
            ny.y=s.y+dir[i][1];
            if(ny.validr()) v.push_back(ny);
        }
        if(v.empty()) return n0;
        if(v.size()==1) return v[0];
        //if (cnt_query <= 10) return ran();
        return nest();
    }

}  // namespace

void succe(){
    println(0,0);
    full_score = 1;
    if(best_score>=T) quitf(_fail,"Reference turns must be below the limit");
    double score=calibrated(std::max(0.0,(T-cnt_query)*1.0/(T-best_score)));
    score = natural_log_score(100.0 * score, cnt_query, best_score, true) / 100.0;
    double unbounded_score=score;
    quitp(score, "cnt_query=%d, Ratio: %.12f, RatioUnbounded: %.12f",  cnt_query,score, unbounded_score);
    exit(0);
}
int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);
    s.x=inf.readInt(),s.y=inf.readInt();
    println(s.x,s.y);///

    best_score=ans.readInt();
    node m,nx;
    for(cnt_query=1;cnt_query<=T;cnt_query++){
        m.x=ouf.readInt();
        m.y=ouf.readInt();
        if(!m.valid()) quitf(_wa, "Invalid coordinate");
        nx=solve(m);
        if(nx.x==n0.x && nx.y==n0.y) succe();
        println(nx.x,nx.y);
        s=nx;
    }
    // for (int i = 1; i <= n; i++) {
    //     std::cerr<<p[i]<<" ";
    // }
    // std::cerr<<std::endl;
    quitf(_wa, "Too many queries");
    return 0;
}
