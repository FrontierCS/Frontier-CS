#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Function to perform a query on a pen.
// Returns true if the pen writes (response 1), false otherwise (response 0).
bool query(int pen) {
    cout << "0 " << pen << endl;
    int res;
    cin >> res;
    return res == 1;
}

void solve() {
    int n;
    cin >> n;
    
    // sets[q] holds the pens that have been queried q times and survived.
    // Ideally, we want to pick pens from sets with low q.
    vector<int> sets[30];
    for (int i = 0; i < n; ++i) {
        sets[0].push_back(i);
    }

    // We want to eliminate the pens with small initial ink.
    // If we eliminate too many, we might damage the high-ink pens too much.
    // If we eliminate too few, we might pick small pens.
    // A heuristic of leaving about half the pens seems safe for N up to 25.
    // For N=25, stopping when ~12 pens are eliminated leaves ~13 pens with initial values >= 12.
    // Even if reduced, finding two with sum >= 25 is likely.
    int elim_target_count = n / 2; 

    // Random engine for shuffling
    mt19937 rng(1337);

    // We try to eliminate pens with initial value 0, then 1, then 2, etc.
    // The pen with initial value 'target' will run out of ink exactly after 'target' queries.
    // So it must reside in some sets[q] with q <= target.
    // To minimize damage to fresh pens (in sets[0]), we search from the most-queried sets downwards.
    for (int target = 0; target < elim_target_count; ++target) {
        bool found = false;
        
        // Search descending to protect sets[0]
        for (int q = target; q >= 0; --q) {
            if (sets[q].empty()) continue;

            // Shuffle to avoid bias
            shuffle(sets[q].begin(), sets[q].end(), rng);

            vector<int> next_level_candidates;
            vector<int> keep_candidates;
            
            for (int pen : sets[q]) {
                if (found) {
                    // If we already found the 0 for this target, the rest are safe in this round
                    keep_candidates.push_back(pen);
                    continue;
                }
                
                bool res = query(pen);
                if (!res) {
                    // Found the pen that ran dry
                    found = true;
                    // It is eliminated
                } else {
                    // Pen wrote successfully, so it has ink remaining.
                    // It has been queried one more time, so move to q+1.
                    next_level_candidates.push_back(pen);
                }
            }
            
            sets[q] = keep_candidates;
            for (int p : next_level_candidates) {
                sets[q+1].push_back(p);
            }

            // If we found the zero, we are done with this target round.
            if (found) break;
        }
    }

    // Collect all surviving pens
    vector<pair<int, int>> survivors; // {queries_performed, pen_id}
    for (int q = 0; q < 30; ++q) {
        for (int p : sets[q]) {
            survivors.push_back({q, p});
        }
    }

    // Sort by number of queries performed (ascending).
    // Pens with fewer queries have more remaining ink relative to their initial value.
    sort(survivors.begin(), survivors.end());

    if (survivors.size() >= 2) {
        cout << "1 " << survivors[0].second << " " << survivors[1].second << endl;
    } else {
        // Fallback, though with the logic above this shouldn't be reached
        // unless n is extremely small (problem says n >= 10).
    }
}

int main() {
    // Optimize I/O operations strictly not needed but good practice
    // However, for interactive problems, we need to be careful with sync.
    // Using default sync is usually safer or manual flush.
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}