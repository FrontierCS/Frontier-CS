#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <unordered_map>
#include <chrono>

using namespace std;

// Suffix Automaton Parameters
// Max length of concatenated string w_u + w_v is around 3000 (based on max_len=1500)
// We allocate enough nodes for the worst case.
const int MAX_STR_LEN = 3200; 
const int MAX_NODES = MAX_STR_LEN * 2 + 100;

struct Node {
    int len, link;
    int next[2];
} nodes[MAX_NODES];

int sz, last;

// Initialize SAM
void sam_init() {
    nodes[0].len = 0;
    nodes[0].link = -1;
    nodes[0].next[0] = nodes[0].next[1] = -1;
    sz = 1;
    last = 0;
}

// Extend SAM with character c (0 for 'X', 1 for 'O')
void sam_extend(int c) {
    int cur = sz++;
    nodes[cur].len = nodes[last].len + 1;
    nodes[cur].next[0] = nodes[cur].next[1] = -1;
    int p = last;
    while (p != -1 && nodes[p].next[c] == -1) {
        nodes[p].next[c] = cur;
        p = nodes[p].link;
    }
    if (p == -1) {
        nodes[cur].link = 0;
    } else {
        int q = nodes[p].next[c];
        if (nodes[p].len + 1 == nodes[q].len) {
            nodes[cur].link = q;
        } else {
            int clone = sz++;
            nodes[clone].len = nodes[p].len + 1;
            nodes[clone].next[0] = nodes[q].next[0];
            nodes[clone].next[1] = nodes[q].next[1];
            nodes[clone].link = nodes[q].link;
            while (p != -1 && nodes[p].next[c] == q) {
                nodes[p].next[c] = clone;
                p = nodes[p].link;
            }
            nodes[q].link = nodes[cur].link = clone;
        }
    }
    last = cur;
}

// Calculate number of distinct substrings
long long calc_distinct() {
    long long ans = 0;
    for (int i = 1; i < sz; i++) {
        ans += nodes[i].len - nodes[nodes[i].link].len;
    }
    return ans;
}

// Helper to get power of a string
long long get_power(const string& s) {
    sam_init();
    for (char c : s) {
        sam_extend(c == 'X' ? 0 : 1);
    }
    return calc_distinct();
}

int n;
vector<string> words;
// Map: power -> {u, v}
unordered_map<long long, pair<int, int>> power_map;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    // Use current time as seed for randomness
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Define length range for generated words.
    // For large N, we need larger lengths to ensure enough distinct power values.
    // Range [700, 1500] gives pairs in [1400, 3000], powers up to ~4.5*10^6.
    // This is sparse enough for N=1000 (10^6 pairs).
    int min_len = 700;
    int max_len = 1500;
    
    // Adjust for small N to optimize score and ensure constraints
    if (n < 100) {
        min_len = n;
        max_len = 3 * n + 20;
        if(max_len < min_len) max_len = min_len + 10;
        if(n <= 10) { min_len = 5; max_len = 20; }
    }

    words.resize(n + 1);
    power_map.reserve(n * n * 2); 

    for (int i = 1; i <= n; ++i) {
        while (true) {
            // Generate a random word
            int len = uniform_int_distribution<int>(min_len, max_len)(rng);
            string s = "";
            s.reserve(len);
            for (int k = 0; k < len; ++k) {
                s += (uniform_int_distribution<int>(0, 1)(rng) ? 'X' : 'O');
            }

            bool ok = true;
            vector<pair<long long, pair<int, int>>> current_batch;
            current_batch.reserve(2 * i);

            // We must ensure that for all j <= i, powers of (i, j) and (j, i) are unique
            // and don't collide with any previously generated pairs.

            // Check (i, i)
            string s3 = s + s;
            long long p3 = get_power(s3);
            if (power_map.find(p3) != power_map.end()) ok = false;
            else current_batch.push_back({p3, {i, i}});

            if (ok) {
                for (int j = 1; j < i; ++j) {
                    // Check (j, i)
                    string s1 = words[j] + s;
                    long long p1 = get_power(s1);
                    if (power_map.find(p1) != power_map.end()) { ok = false; break; }
                    current_batch.push_back({p1, {j, i}});

                    // Check (i, j)
                    string s2 = s + words[j];
                    long long p2 = get_power(s2);
                    if (power_map.find(p2) != power_map.end()) { ok = false; break; }
                    current_batch.push_back({p2, {i, j}});
                }
            }

            if (ok) {
                // Check for duplicates within the current batch itself
                sort(current_batch.begin(), current_batch.end());
                for (size_t k = 0; k + 1 < current_batch.size(); ++k) {
                    if (current_batch[k].first == current_batch[k+1].first) {
                        ok = false; break;
                    }
                }
            }

            // If valid, commit the word and updates to map
            if (ok) {
                words[i] = s;
                for (auto& entry : current_batch) {
                    power_map[entry.first] = entry.second;
                }
                break;
            }
            // If not valid, loop repeats and generates a new candidate for w_i
        }
    }

    // Output all words
    for (int i = 1; i <= n; ++i) {
        cout << words[i] << "\n";
    }
    cout.flush();

    // Process queries
    int q;
    if (cin >> q) {
        while (q--) {
            long long p;
            cin >> p;
            auto it = power_map.find(p);
            if (it != power_map.end()) {
                cout << it->second.first << " " << it->second.second << "\n";
            } else {
                // This case should theoretically not happen given problem constraints
                cout << "1 1\n";
            }
            cout.flush();
        }
    }

    return 0;
}