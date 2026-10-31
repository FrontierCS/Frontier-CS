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
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char **argv) {
    registerTestlibCmd(argc, argv);
    int n=inf.readInt(1,500000), m=inf.readInt(1,500000);
    for(int i=0;i<10;i++) inf.readInt(); // legacy metadata, NOT score thresholds
    unordered_set<long long> edges;
    auto key=[&](int u,int v){return 1LL*u*(n+1)+v;};
    for(int i=0;i<m;i++) {
        int u=inf.readInt(1,n),v=inf.readInt(1,n); edges.insert(key(u,v));
    }
    auto path=[&](InStream &stream, bool reference) {
        int k=stream.readInt(reference?1:0,n);
        vector<char> seen(n+1); int prev=0;
        for(int i=0;i<k;i++) {
            int v=stream.readInt(1,n);
            if(seen[v] || (i && !edges.count(key(prev,v))))
                quitf(reference?_fail:_wa,"Invalid %s path",reference?"reference":"participant");
            seen[v]=1; prev=v;
        }
        if(!stream.seekEof()) quitf(reference?_fail:_pe,"Extra path tokens");
        return k;
    };
    int best=path(ans,true), length=path(ouf,false);
    double score=calibrated((double)length/best);
    score = natural_log_score(100.0 * score, length, best, false) / 100.0;
    quitp(score,"Length=%d Reference=%d Ratio: %.12f RatioUnbounded: %.12f",length,best,score,score);
}
