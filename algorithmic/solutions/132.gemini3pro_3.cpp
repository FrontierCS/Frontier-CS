#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    // We use a strategy based on modular arithmetic (Chinese Remainder Theorem).
    // Moduli: 5, 7, 8, 9. 
    // Sum = 29, so we use 29 robots. This is <= 30 for max score tier (or close to).
    // LCM(5, 7, 8, 9) = 2520, which is larger than the range of positions + slack.
    // To avoid adversarial cases where the solution is ambiguous (ghost pairs),
    // we randomly permute the positions 1..1000.
    
    vector<int> moduli = {5, 7, 8, 9};
    
    // Mapping from real position to "virtual" position
    vector<int> p(1001);
    iota(p.begin(), p.end(), 0);
    unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
    shuffle(p.begin() + 1, p.end(), std::default_random_engine(seed));
    
    // Reverse mapping to retrieve real position
    vector<int> rev_p(1001);
    for(int i=1; i<=1000; ++i) rev_p[p[i]] = i;

    // Send queries
    for (int m : moduli) {
        for (int r = 0; r < m; ++r) {
            vector<int> query_pos;
            query_pos.reserve(1000/m + 2);
            for (int i = 1; i <= 1000; ++i) {
                // Query real position i if its virtual position p[i] has remainder r modulo m
                if (p[i] % m == r) {
                    query_pos.push_back(i);
                }
            }
            
            cout << "? " << query_pos.size();
            for (int x : query_pos) cout << " " << x;
            cout << "\n";
        }
    }
    cout.flush();

    // Retrieve results
    cout << "@" << endl;
    int L;
    cin >> L;
    vector<int> responses(L);
    for (int i = 0; i < L; ++i) cin >> responses[i];

    // Process results into sets of residues for each modulus
    vector<vector<int>> residues(moduli.size());
    int current_robot = 0;
    for (int i = 0; i < (int)moduli.size(); ++i) {
        int m = moduli[i];
        for (int r = 0; r < m; ++r) {
            if (responses[current_robot]) {
                residues[i].push_back(r);
            }
            current_robot++;
        }
    }

    // Identify candidate virtual positions consistent with observed residues
    vector<int> candidates;
    candidates.reserve(16);
    for (int v = 1; v <= 1000; ++v) { 
        bool ok = true;
        for (int i = 0; i < (int)moduli.size(); ++i) {
            bool found = false;
            for (int r : residues[i]) {
                if (v % moduli[i] == r) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                ok = false;
                break;
            }
        }
        if (ok) candidates.push_back(v);
    }

    int ansA = 1, ansB = 1;

    // Find the pair of candidates that exactly matches the observed residue sets
    for (size_t i = 0; i < candidates.size(); ++i) {
        for (size_t j = i; j < candidates.size(); ++j) {
            int u = candidates[i];
            int v = candidates[j];
            
            bool match = true;
            for (int k = 0; k < (int)moduli.size(); ++k) {
                int r1 = u % moduli[k];
                int r2 = v % moduli[k];
                
                int min_r = (r1 < r2) ? r1 : r2;
                int max_r = (r1 < r2) ? r2 : r1;
                
                if (r1 == r2) {
                    // Expect exactly one residue equal to r1
                    if (residues[k].size() != 1 || residues[k][0] != r1) {
                         match = false; break; 
                    }
                } else {
                    // Expect exactly two residues: min_r and max_r
                    // residues[k] is naturally sorted by the query order (0..m-1)
                    if (residues[k].size() != 2 || residues[k][0] != min_r || residues[k][1] != max_r) {
                        match = false; break;
                    }
                }
            }
            
            if (match) {
                ansA = rev_p[u];
                ansB = rev_p[v];
                goto done;
            }
        }
    }

done:
    cout << "! " << ansA << " " << ansB << endl;

    return 0;
}