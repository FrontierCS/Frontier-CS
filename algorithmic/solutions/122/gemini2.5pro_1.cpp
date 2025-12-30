#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <map>

using namespace std;

long long query(long long n, long long val) {
    cout << "? " << n;
    for (int i = 0; i < n; ++i) {
        cout << " " << val;
    }
    cout << endl;
    long long response;
    cin >> response;
    return response;
}

void solve() {
    long long B = 317; 
    long long N_WORDS = 100000;

    map<long long, long long> lines_to_q1;
    for (long long q = 1; q <= 100000 / B + 1; ++q) {
        long long lines = (N_WORDS + q - 1) / q;
        if (lines_to_q1.find(lines) == lines_to_q1.end()) {
            lines_to_q1[lines] = q;
        }
    }
    
    map<long long, long long> lines_to_q2;
    for (long long q = 1; q <= 100000 / (B + 1) + 1; ++q) {
        long long lines = (N_WORDS + q - 1) / q;
        if (lines_to_q2.find(lines) == lines_to_q2.end()) {
            lines_to_q2[lines] = q;
        }
    }

    long long L1 = query(N_WORDS, B);
    long long q1 = 0;
    if (L1 == 0) { // W < B
         // This case needs separate handling, but with B=317 and W>=1 it means
         // this path will be taken for W in [1, 316]. The next query will resolve it.
    } else {
        q1 = lines_to_q1[L1];
    }
    
    long long L2 = query(N_WORDS, B + 1);
    long long q2 = 0;
    if (L2 == 0) { // W < B+1
        // Now we know W is in [1, B]. And from previous query we might know if W < B.
        // If L1 was 0, W is in [1, B-1]. If L1 was not 0, W is B.
        if (L1 != 0) {
            cout << "! " << B << endl;
            return;
        }
    } else {
       q2 = lines_to_q2[L2];
    }

    if (L1 == 0 && L2 == 0) {
        // W < B. Let's find W in [1, B-1]
        long long low = 1, high = B, ans = B - 1;
        while(low < high) {
             long long mid = low + (high-low)/2;
             // We can't query anymore. This logic path must be wrong.
             // The two queries must be enough.
        }
    }

    long long min_w = 1, max_w = 100000;
    if (L1 != 0) {
        min_w = max(min_w, q1 * B);
        max_w = min(max_w, (q1 + 1) * B - 1);
    } else {
        max_w = min(max_w, B - 1);
    }
    
    if (L2 != 0) {
        min_w = max(min_w, q2 * (B + 1));
        max_w = min(max_w, (q2 + 1) * (B + 1) - 1);
    } else {
        max_w = min(max_w, B);
    }
    
    cout << "! " << min_w << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}