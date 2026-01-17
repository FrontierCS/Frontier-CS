#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// State of the beam
struct State {
    int ends[4]; // End values of the 4 subsequences
    int score;   // Number of elements strictly included in the chains
};

// Candidate for the next beam
struct Candidate {
    int ends[4];
    int score;
    int parent_idx;
    int act; // Action taken: 0-3 for adding to bucket, 4 for skip

    // Comparator for sorting candidates
    // Primary: Score (descending)
    // Secondary: Tie-breaking heuristics for 'ends'
    // For increasing sequences (0, 2), smaller end is better.
    // For decreasing sequences (1, 3), larger end is better.
    // We want the "better" candidates to come first (be "smaller" in sort order? No, sort is ascending).
    // We sort such that "better" elements are at the beginning.
    // Since std::sort is ascending, we define operator< such that A < B means A is better than B.
    // So we want:
    // Higher score < Lower score
    // If scores equal:
    // Inc: Smaller end < Larger end
    // Dec: Larger end < Smaller end
    bool operator<(const Candidate& other) const {
        if (score != other.score) {
            return score > other.score;
        }
        if (ends[0] != other.ends[0]) return ends[0] < other.ends[0];
        if (ends[1] != other.ends[1]) return ends[1] > other.ends[1];
        if (ends[2] != other.ends[2]) return ends[2] < other.ends[2];
        return ends[3] > other.ends[3];
    }
};

// Backtrace info to reconstruct solution
struct Backtrace {
    uint16_t parent;
    uint8_t act;
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
    }

    // Beam Search Parameters
    // K is the beam width.
    // With N=100,000, K=60 ensures total operations ~3.6e8, which fits within typical 1-2s limits.
    const int K = 60; 

    // Current beam
    vector<State> beam;
    beam.reserve(K);

    // Initial state
    State initial;
    // Buckets 0 and 2 are increasing: init with 0
    // Buckets 1 and 3 are decreasing: init with n+1
    initial.ends[0] = 0;
    initial.ends[1] = n + 1;
    initial.ends[2] = 0;
    initial.ends[3] = n + 1;
    initial.score = 0;
    beam.push_back(initial);

    // History for reconstruction
    // history[i] stores the transitions taken to reach the states in beam after processing p[i]
    vector<vector<Backtrace>> history(n);

    // Reuse candidates vector to avoid reallocation
    vector<Candidate> candidates;
    candidates.reserve(K * 5 + 5);

    for (int i = 0; i < n; ++i) {
        int val = p[i];
        candidates.clear();

        // Generate candidates from current beam
        for (int b_idx = 0; b_idx < (int)beam.size(); ++b_idx) {
            const auto& st = beam[b_idx];

            // Action 0: Append to increasing seq a
            if (val > st.ends[0]) {
                Candidate cand;
                for(int k=0; k<4; ++k) cand.ends[k] = st.ends[k];
                cand.ends[0] = val;
                cand.score = st.score + 1;
                cand.parent_idx = b_idx;
                cand.act = 0;
                candidates.push_back(cand);
            }

            // Action 1: Append to decreasing seq b
            if (val < st.ends[1]) {
                Candidate cand;
                for(int k=0; k<4; ++k) cand.ends[k] = st.ends[k];
                cand.ends[1] = val;
                cand.score = st.score + 1;
                cand.parent_idx = b_idx;
                cand.act = 1;
                candidates.push_back(cand);
            }

            // Action 2: Append to increasing seq c
            if (val > st.ends[2]) {
                Candidate cand;
                for(int k=0; k<4; ++k) cand.ends[k] = st.ends[k];
                cand.ends[2] = val;
                cand.score = st.score + 1;
                cand.parent_idx = b_idx;
                cand.act = 2;
                candidates.push_back(cand);
            }

            // Action 3: Append to decreasing seq d
            if (val < st.ends[3]) {
                Candidate cand;
                for(int k=0; k<4; ++k) cand.ends[k] = st.ends[k];
                cand.ends[3] = val;
                cand.score = st.score + 1;
                cand.parent_idx = b_idx;
                cand.act = 3;
                candidates.push_back(cand);
            }

            // Action 4: Skip (Assign to waste/any bucket later)
            {
                Candidate cand;
                for(int k=0; k<4; ++k) cand.ends[k] = st.ends[k];
                cand.score = st.score;
                cand.parent_idx = b_idx;
                cand.act = 4;
                candidates.push_back(cand);
            }
        }

        // Select top K candidates
        sort(candidates.begin(), candidates.end());

        beam.clear();
        history[i].reserve(K);

        // Deduplicate and fill beam
        for (const auto& cand : candidates) {
            if (beam.size() >= K) break;

            // Simple linear scan to deduplicate ends is efficient enough for small K
            bool exists = false;
            for (const auto& existing : beam) {
                bool same = true;
                for(int k=0; k<4; ++k) {
                    if (existing.ends[k] != cand.ends[k]) {
                        same = false;
                        break;
                    }
                }
                if (same) {
                    exists = true;
                    break;
                }
            }

            if (!exists) {
                State next_st;
                for(int k=0; k<4; ++k) next_st.ends[k] = cand.ends[k];
                next_st.score = cand.score;
                beam.push_back(next_st);

                history[i].push_back({(uint16_t)cand.parent_idx, (uint8_t)cand.act});
            }
        }
    }

    // Reconstruct solution
    // The first state in beam is the best because of sorting
    int curr_idx = 0;
    
    // Array to store result subsequences
    vector<int> res[4];
    
    // Trace back actions
    vector<int> actions(n);
    for (int i = n - 1; i >= 0; --i) {
        Backtrace bt = history[i][curr_idx];
        actions[i] = bt.act;
        curr_idx = bt.parent;
    }

    // Build the subsequences
    for (int i = 0; i < n; ++i) {
        int act = actions[i];
        if (act == 4) act = 0; // Assign skipped elements to the first bucket arbitrarily
        res[act].push_back(p[i]);
    }

    // Output
    cout << res[0].size() << " " << res[1].size() << " " << res[2].size() << " " << res[3].size() << "\n";
    for (int k = 0; k < 4; ++k) {
        for (int i = 0; i < (int)res[k].size(); ++i) {
            cout << res[k][i] << (i == (int)res[k].size() - 1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}