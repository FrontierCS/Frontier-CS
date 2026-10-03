#include "testlib.h"
#include <vector>
#include <algorithm>
using namespace std;

int main(int argc, char * argv[]) {
    registerTestlibCmd(argc, argv);
    
    int T = inf.readInt();
    int total_cases = 0;
    double total_ratio = 0;
    double total_unbounded_ratio = 0;
    
    for (int tc = 1; tc <= T; tc++) {
        int n = inf.readInt();
        int m = inf.readInt();
        long long c = inf.readLong();
        
        vector<long long> a(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            long long ai = inf.readLong();
            a[i] = a[i-1] + ai;
        }
        
        vector<long long> b(m + 1, 0);
        for (int i = 1; i <= m; i++) {
            long long bi = inf.readLong();
            b[i] = b[i-1] + bi;
        }
        
        // Read reference answer
        long long ref_score = ans.readLong();
        
        /** Changing to one line for test case */
        long long participant_score = ouf.readLong();
        
        if (participant_score != ref_score) {
            quitf(_wa, "Test case %d: answer %lld does not match reference %lld", 
                tc, participant_score, ref_score);
        }
        
        /** particpant score and ref score are equal */
        
        double ratio = 0.8; // min(1.0, (double)participant_score / ref_score * 0.8);
        double unbounded_ratio = 0.8; // (double)participant_score / ref_score * 0.8;
        
        total_ratio += ratio;
        total_unbounded_ratio += unbounded_ratio;
        total_cases++;
    }
    
    total_ratio /= total_cases;
    total_unbounded_ratio /= total_cases;
    double score = total_ratio * 100;
    double unbounded_score = total_unbounded_ratio * 100;
    
    if (!ouf.seekEof()) {
        quitf(_wa, "Extra output found");
    }
    
    string msg = format(
        "Correct! Ratio: %.6f (Score: %.2f). RatioUnbounded: %.6f (ScoreUnbounded: %.2f)",
        total_ratio, score, total_unbounded_ratio, unbounded_score);
    
    quitp(total_ratio, msg.c_str());
}