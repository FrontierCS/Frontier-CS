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

static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include <string>
#include <cassert>


namespace {

    constexpr int N_MAX = 1000, M_MAX = 1002, Q_MAX = 1000;
    int N;
    std::string S;
    int query_count = 0, query_m_max = 0, full_score = 1;
    int a[M_MAX + 10], b[M_MAX + 10];

    int Query() {
        int memory = 0;
        for (int i = 0; i < N; i++) {
            if (S[i] == '0') {
            memory = a[memory];
            }
            if (S[i] == '1') {
            memory = b[memory];
            }
        }
        return memory;
    }
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);
    N=inf.readInt();
    S=ans.readString();
    assert((int)S.size()==N);
    println(N);
    int op=ouf.readInt();
    while(op){
        query_count++;
        if(query_count>Q_MAX) quitf(_wa, "Too many queries");
        int m=ouf.readInt();
        if(!(1<=m && m<=M_MAX)) quitf(_wa, "Invalid m");
        for(int i=0;i<m;i++) a[i]=ouf.readInt();
        for(int i=0;i<m;i++) b[i]=ouf.readInt();
        for(int i=0;i<m;i++){
            if(!(0<=a[i] && a[i]<m)) quitf(_wa, "Invalid a[%d]", i);
            if(!(0<=b[i] && b[i]<m)) quitf(_wa, "Invalid b[%d]", i);
        }
        if(m>query_m_max) query_m_max=m;

        int res=Query();
        println(res);

        op=ouf.readInt();
    }
    char ch=ouf.readChar();
    std::string s = ouf.readString();
    if ((int)s.size() != N) quitf(_wa, "Invalid guess length");
    for(int i=0;i<N;i++){
        if(!(s[i]=='0' || s[i]=='1')) quitf(_wa, "Invalid character in guess");
        if(s[i]!=S[i]) quitf(_wa, "Wrong guess");
    }
    // Continuous version of the original quadratic scale, extended below M=102.
    double r = (10.0 + (1002.0-query_m_max)*(1002.0-query_m_max)/9000.0)/100.0;
    double score = referenceScore(r);
    score = natural_log_score(100.0 * score, query_m_max, 102, true) / 100.0;
    quitp(score, "query_m_max=%d, Ratio: %.12f, RatioUnbounded: %.12f", query_m_max, score, score);
    return 0;
}
