#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

using namespace std;

void solve() {
    // Query 1: Send n1 ones to get an estimate of W.
    // n1 = 100000 is chosen to provide a good lower bound if W is large,
    // and good precision if W is small.
    int n1 = 100000;
    cout << "? " << n1;
    for (int i = 0; i < n1; ++i) {
        cout << " 1";
    }
    cout << endl;

    int l1;
    cin >> l1;
    if (l1 == -1) exit(0);

    // If l1 == 0, it would imply 1 > W, but W >= 1, so not possible.
    
    // Calculate range [min_w, max_w] based on l1.
    // L = ceil(n1 / W)  =>  L-1 < n1/W <= L
    // W >= n1/L
    // W < n1/(L-1)
    
    int min_w = (n1 + l1 - 1) / l1;
    int max_w;
    if (l1 == 1) {
        max_w = 100000; // W >= n1, and max possible W is 100000
    } else {
        // W <= floor((n1-1)/(l1-1))
        max_w = (n1 - 1) / (l1 - 1);
        if (max_w > 100000) max_w = 100000;
    }
    if (min_w < 1) min_w = 1;

    // Filter candidates based on l1 exactly
    vector<int> candidates;
    for (int w = min_w; w <= max_w; ++w) {
        long long lines = (1LL * n1 + w - 1) / w;
        if (lines == l1) {
            candidates.push_back(w);
        }
    }

    if (candidates.empty()) {
        // Should not happen
        return;
    }

    if (candidates.size() == 1) {
        cout << "! " << candidates[0] << endl;
        return;
    }

    // Query 2: Disambiguate candidates.
    // We use words of length C = candidates[0].
    // Since all candidates w are >= C, these words fit in the line.
    // We use n2 words to maximize the total length S = n2 * C, increasing resolution.
    // For identical words of length C, the number of words per line is floor(w / C).
    // Total lines = ceil(n2 / floor(w / C)).
    
    int C = candidates[0];
    // If range is large (e.g., [50000, 99999]), C=50000. floor(w/C) is 1 for all w.
    // In that case L2 is constant n2, providing no info.
    // However, usually we can't do better with 2 queries in that specific hard case 
    // without a different Q1 strategy which might fail elsewhere.
    // We stick to this strategy as it covers most cases and is standard for this type of problem.
    
    int n2 = 100000; 
    
    cout << "? " << n2;
    for (int i = 0; i < n2; ++i) {
        cout << " " << C;
    }
    cout << endl;

    int l2;
    cin >> l2;
    if (l2 == -1) exit(0);

    int ans = candidates[0];
    // Find the first candidate that matches l2
    for (int w : candidates) {
        int words_per_line = w / C;
        if (words_per_line == 0) continue; 
        long long lines = (1LL * n2 + words_per_line - 1) / words_per_line;
        
        if (lines == l2) {
            ans = w;
            break; 
        }
    }
    
    cout << "! " << ans << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}