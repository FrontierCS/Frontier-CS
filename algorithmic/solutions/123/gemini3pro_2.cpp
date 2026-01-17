#include <iostream>
#include <vector>
#include <numeric>
#include <string>

using namespace std;

int main() {
    // Optimize I/O operations for speed, though flushing is required for interactivity.
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // S0: Candidates consistent with the previous answer being Truth.
    // S1: Candidates consistent with the previous answer being a Lie (so next MUST be Truth).
    // Initially, no queries asked, so all candidates are in S0 (neutral start).
    vector<int> s0(n);
    iota(s0.begin(), s0.end(), 1);
    vector<int> s1;

    // We continue querying until we have 2 or fewer candidates left.
    // The "potential function" of the sets reduces by a factor of roughly 1.618 each step.
    // 53 queries are sufficient for N=100,000.
    while (s0.size() + s1.size() > 2) {
        // We split both sets roughly in half to balance the worst-case potential.
        int k0 = s0.size() / 2;
        int k1 = s1.size() / 2;

        // Construct query set S containing first k0 of s0 and first k1 of s1
        vector<int> S;
        S.reserve(k0 + k1);
        for (int i = 0; i < k0; ++i) S.push_back(s0[i]);
        for (int i = 0; i < k1; ++i) S.push_back(s1[i]);

        // Ask query
        cout << "? " << S.size();
        for (int x : S) cout << " " << x;
        cout << endl; // Flush output

        string resp;
        cin >> resp;

        vector<int> next_s0, next_s1;
        next_s0.reserve(s0.size() + s1.size());
        next_s1.reserve(s0.size());

        if (resp == "YES") {
            // Answer YES means:
            // Truth: x in S
            // Lie: x not in S

            // Candidates in S0:
            // - If in S: Consistent with Truth -> stay in S0
            // - If not in S: Inconsistent with Truth (must be Lie) -> move to S1
            for (int i = 0; i < k0; ++i) next_s0.push_back(s0[i]);
            for (int i = k0; i < s0.size(); ++i) next_s1.push_back(s0[i]);

            // Candidates in S1 (require Prev=Lie):
            // - If in S: Consistent with Truth. (Prev=Lie, Curr=Truth is OK) -> move to S0
            // - If not in S: Inconsistent with Truth. (Prev=Lie, Curr=Lie is Forbidden) -> Eliminated
            for (int i = 0; i < k1; ++i) next_s0.push_back(s1[i]);
        } else {
            // Answer NO means:
            // Truth: x not in S
            // Lie: x in S

            // Candidates in S0:
            // - If in S: Inconsistent with Truth (must be Lie) -> move to S1
            // - If not in S: Consistent with Truth -> stay in S0
            for (int i = 0; i < k0; ++i) next_s1.push_back(s0[i]);
            for (int i = k0; i < s0.size(); ++i) next_s0.push_back(s0[i]);

            // Candidates in S1:
            // - If in S: Inconsistent with Truth. (Prev=Lie, Curr=Lie Forbidden) -> Eliminated
            // - If not in S: Consistent with Truth. (Prev=Lie, Curr=Truth OK) -> move to S0
            for (int i = k1; i < s1.size(); ++i) next_s0.push_back(s1[i]);
        }

        s0 = next_s0;
        s1 = next_s1;
    }

    // We have at most 2 candidates. We can make up to 2 guesses.
    // Just guess them one by one.
    vector<int> candidates = s0;
    candidates.insert(candidates.end(), s1.begin(), s1.end());

    for (int g : candidates) {
        cout << "! " << g << endl;
        string resp;
        cin >> resp;
        if (resp == ":)") break;
    }

    return 0;
}