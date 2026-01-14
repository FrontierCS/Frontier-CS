#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Represents the state of our 4 subsequences at a given step
// ta, tc: tails of increasing subsequences (LIS of a, LIS of c)
// tb, td: tails of decreasing subsequences (LDS of b, LDS of d)
struct State {
    int ta, tb, tc, td;
    int score; // Number of elements successfully added to chains
    int parent_idx; // Index of the parent state in the previous beam
    int choice; // Decision made: 0=a, 1=b, 2=c, 3=d, 4=waste

    // Heuristic for tie-breaking: larger potential is better
    // We want small increasing tails and large decreasing tails
    int potential() const {
        return tb + td - ta - tc;
    }
};

// Compact storage for reconstructing the path
struct SavedStep {
    unsigned short parent;
    unsigned char choice;
};

// Global history array. history[i] stores the beam states' metadata at step i.
vector<SavedStep> history[100005];
int p[100005];

// Comparator for sorting states in the beam
// Primary: Score (higher is better)
// Secondary: Potential (higher is better)
bool compareStates(const State& a, const State& b) {
    if (a.score != b.score) return a.score > b.score;
    return a.potential() > b.potential();
}

// Check if two states have identical tails (used for deduplication)
bool sameTails(const State& a, const State& b) {
    return a.ta == b.ta && a.tb == b.tb && a.tc == b.tc && a.td == b.td;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;
    for (int i = 0; i < n; ++i) cin >> p[i];

    // Beam search width
    const int K = 120;
    
    // Current beam of states
    vector<State> beam;
    beam.reserve(K * 5);
    // Initial state: increasing tails 0, decreasing tails n+1 (out of bounds)
    beam.push_back({0, n + 1, 0, n + 1, 0, -1, -1});

    // Buffer for next candidates
    vector<State> next_candidates;
    next_candidates.reserve(K * 5);

    for (int i = 0; i < n; ++i) {
        int val = p[i];
        next_candidates.clear();

        for (int j = 0; j < beam.size(); ++j) {
            const auto& s = beam[j];
            
            // Option 1: Append to 'a' (increasing)
            if (val > s.ta) {
                next_candidates.push_back({val, s.tb, s.tc, s.td, s.score + 1, j, 0});
            }
            // Option 2: Append to 'b' (decreasing)
            if (val < s.tb) {
                next_candidates.push_back({s.ta, val, s.tc, s.td, s.score + 1, j, 1});
            }
            // Option 3: Append to 'c' (increasing)
            if (val > s.tc) {
                next_candidates.push_back({s.ta, s.tb, val, s.td, s.score + 1, j, 2});
            }
            // Option 4: Append to 'd' (decreasing)
            if (val < s.td) {
                next_candidates.push_back({s.ta, s.tb, s.tc, val, s.score + 1, j, 3});
            }
            
            // Option 5: Waste (don't extend any tracked chain)
            // The element will be assigned to 'a' later, but tails/score don't update
            next_candidates.push_back({s.ta, s.tb, s.tc, s.td, s.score, j, 4});
        }

        // Sort candidates to find the best ones
        sort(next_candidates.begin(), next_candidates.end(), compareStates);

        // Select top K unique states
        beam.clear();
        if (!next_candidates.empty()) {
            beam.push_back(next_candidates[0]);
            for (size_t k = 1; k < next_candidates.size(); ++k) {
                if (beam.size() >= K) break;
                // Since sorted by score, the first occurrence of a tail-config is the best one
                if (!sameTails(next_candidates[k], beam.back())) {
                    beam.push_back(next_candidates[k]);
                }
            }
        }
        
        // Save history for reconstruction
        history[i].resize(beam.size());
        for(int j = 0; j < beam.size(); ++j) {
            history[i][j] = {(unsigned short)beam[j].parent_idx, (unsigned char)beam[j].choice};
        }
    }

    // Reconstruct the solution
    // beam[0] is the state with the highest score at the last step
    int cur_idx = 0; 
    vector<int> choices(n);
    for (int i = n - 1; i >= 0; --i) {
        choices[i] = history[i][cur_idx].choice;
        cur_idx = history[i][cur_idx].parent;
    }

    vector<int> a, b, c, d_seq;
    for (int i = 0; i < n; ++i) {
        int val = p[i];
        int ch = choices[i];
        if (ch == 0 || ch == 4) a.push_back(val); // Assign 'waste' to a
        else if (ch == 1) b.push_back(val);
        else if (ch == 2) c.push_back(val);
        else if (ch == 3) d_seq.push_back(val);
    }

    // Output results
    cout << a.size() << " " << b.size() << " " << c.size() << " " << d_seq.size() << "\n";
    
    auto print_v = [&](const vector<int>& v) {
        for (int i = 0; i < v.size(); ++i) cout << v[i] << (i + 1 == v.size() ? "" : " ");
        cout << "\n";
    };
    
    print_v(a);
    print_v(b);
    print_v(c);
    print_v(d_seq);

    return 0;
}