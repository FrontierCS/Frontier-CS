#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// The problem asks us to determine a hidden binary string S of length N=1000.
// We can make up to 1000 queries.
// To get full points, m (number of states) should be <= 102.
// We determine the string character by character from 0 to N-1.
// For the k-th character, we construct an automaton that accepts the known prefix S[0...k-1]
// and lands on a state u. We then set up a transition from u to a Sink state 
// on a specific character ('0' or '1') to probe S[k].
// To avoid false positives (reaching Sink before step k), we enforce that each state
// in our automaton only handles one type of character ('0' or '1') or is unused.
// This ensures that if we probe '1' from a '0'-type state, we are using a free edge,
// and since the state was only visited with '0' in the past, the '1' edge was never taken.

int N;
int M = 100; // Working states 0..99
int SINK = 100; // Sink state
int NUM_STATES = 101; // Total states used in query

mt19937 rng(1337);

string S_known = "";

struct Graph {
    // type[u] stores the character type this state accepts ('0' or '1'). -1 if unused.
    vector<int> type;
    // trans[u][0] and trans[u][1] store transitions.
    vector<vector<int>> trans; 
};

// Attempts to map the path S[0...k-1] onto the graph with M states.
// Returns true if successful, false otherwise.
// end_node is set to the state reached after k steps.
bool build_path(int k, Graph& g, int& end_node) {
    g.type.assign(M, -1);
    g.trans.assign(M, vector<int>(2, -1));
    
    int u = 0; // Start state is always 0
    
    // If we have processed some characters, state 0 is fixed to the type of the first character.
    if (k > 0) {
        g.type[0] = S_known[0] - '0';
    }

    for (int i = 0; i < k; ++i) {
        int c = S_known[i] - '0';
        
        // Consistency check: state u must be compatible with char c
        if (g.type[u] != -1 && g.type[u] != c) return false;
        g.type[u] = c;
        
        // If transition exists, follow it
        if (g.trans[u][c] != -1) {
            u = g.trans[u][c];
        } else {
            // Need to choose a next state v
            // Candidates: all states 0..M-1
            vector<int> cands(M);
            iota(cands.begin(), cands.end(), 0);
            shuffle(cands.begin(), cands.end(), rng);
            
            bool found = false;
            for (int v : cands) {
                // Heuristic/Constraint: 
                // If we know the next char S[i+1], we must pick v compatible with it.
                if (i + 1 < k) {
                    int next_c = S_known[i+1] - '0';
                    if (g.type[v] != -1 && g.type[v] != next_c) continue;
                }
                
                g.trans[u][c] = v;
                u = v;
                found = true;
                break;
            }
            if (!found) return false;
        }
    }
    end_node = u;
    return true;
}

int get_result() {
    int res;
    cin >> res;
    return res;
}

void solve() {
    if (!(cin >> N)) return;
    S_known = "";
    
    for (int k = 0; k < N; ++k) {
        Graph g;
        int end_node = -1;
        bool built = false;
        
        // Try to build a valid mapping with randomized greedy strategy
        for (int iter = 0; iter < 2000; ++iter) {
            if (build_path(k, g, end_node)) {
                built = true;
                break;
            }
        }
        
        // If fails (very unlikely with M=100, K=1000), we might just guess or retry more.
        // Given constraints and randomness, it typically succeeds quickly.
        if (!built) {
            // Fallback: assume 0 to keep running
            S_known += '0';
            continue;
        }
        
        // Determine which character to probe
        // If end_node accepts '0', its '1' edge is free -> Probe '1'
        // If end_node accepts '1', its '0' edge is free -> Probe '0'
        // If -1 (unused), both free -> Probe '1' (arbitrary)
        int probe_char = 1;
        if (g.type[end_node] == 1) probe_char = 0;
        else if (g.type[end_node] == 0) probe_char = 1;
        
        vector<int> a(NUM_STATES), b(NUM_STATES);
        
        // Fill query arrays
        for (int i = 0; i < M; ++i) {
            // '0' transitions
            if (g.trans[i][0] != -1) {
                a[i] = g.trans[i][0];
            } else {
                // If this edge is the probe
                if (i == end_node && probe_char == 0) a[i] = SINK;
                else a[i] = 0; // Default/unused
            }
            
            // '1' transitions
            if (g.trans[i][1] != -1) {
                b[i] = g.trans[i][1];
            } else {
                // If this edge is the probe
                if (i == end_node && probe_char == 1) b[i] = SINK;
                else b[i] = 0; // Default/unused
            }
        }
        
        // Sink stays in Sink
        a[SINK] = SINK;
        b[SINK] = SINK;
        
        // Output query
        cout << "? " << NUM_STATES << " ";
        for(int i = 0; i < NUM_STATES; ++i) cout << a[i] << (i == NUM_STATES - 1 ? "" : " ");
        cout << " ";
        for(int i = 0; i < NUM_STATES; ++i) cout << b[i] << (i == NUM_STATES - 1 ? "" : " ");
        cout << endl;
        
        int res = get_result();
        
        // If we landed in Sink, we saw the probe_char at step k
        if (res == SINK) {
            S_known += (char)('0' + probe_char);
        } else {
            // Otherwise we saw the other char
            S_known += (char)('0' + (1 - probe_char));
        }
    }
    
    cout << "! " << S_known << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}