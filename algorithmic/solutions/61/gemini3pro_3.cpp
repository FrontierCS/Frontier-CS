#include <iostream>
#include <vector>
#include <numeric>
#include <queue>
#include <algorithm>

using namespace std;

typedef long long ll;

const ll INF = 1e18;

// Event structure for Priority Queue
struct Event {
    ll trigger_exp;
    int chain_id;
    int next_level;

    // Min-heap based on trigger_exp
    bool operator>(const Event& other) const {
        return trigger_exp > other.trigger_exp;
    }
};

// Chain structure to track state of each potential character start
struct Chain {
    ll start_p;
    ll base_dp;
    int current_level;
};

// Global arrays to reuse memory
ll a[500005];
ll b[500005];
ll Q[500005]; // Prefix sum of b
ll dp[500005];
Chain chains[500005];

void solve() {
    int n, m;
    ll c;
    if (!(cin >> n >> m >> c)) return;

    for (int i = 1; i <= n; ++i) cin >> a[i];
    for (int i = 1; i <= m; ++i) cin >> b[i];

    // Compute prefix sums of b
    Q[0] = 0;
    for (int i = 1; i <= m; ++i) {
        Q[i] = Q[i-1] + b[i];
    }

    // Determine start level (max k such that Q[k] == 0)
    // This handles cases where initial levels require 0 EXP
    int start_level = 0;
    while (start_level < m && Q[start_level+1] == 0) {
        start_level++;
    }

    // Priority Queue for events
    priority_queue<Event, vector<Event>, greater<Event>> pq;

    ll current_P = 0;
    ll global_max = -INF;

    // Initialize with dummy chain 0 (representing starting a character at day 1)
    // dp[0] = 0 is the base score
    dp[0] = 0;
    chains[0] = {0, 0, start_level};
    
    // Initial global max contribution from chain 0
    ll val0 = dp[0] + start_level;
    global_max = val0;

    // Add first event for chain 0 if it can level up
    if (start_level < m) {
        pq.push({chains[0].start_p + Q[start_level + 1], 0, start_level + 1});
    }

    for (int i = 1; i <= n; ++i) {
        current_P += a[i];

        // Process all events that are triggered by current total EXP
        while (!pq.empty() && pq.top().trigger_exp <= current_P) {
            Event e = pq.top();
            pq.pop();

            int id = e.chain_id;
            
            // Pruning optimization: 
            // If the maximum possible value this chain can ever achieve (base_dp + m)
            // is less than or equal to the current global maximum, this chain is useless.
            if (chains[id].base_dp + m <= global_max) {
                continue; 
            }
            
            // Update chain level
            chains[id].current_level = e.next_level;
            
            // Update global max
            ll val = chains[id].base_dp + chains[id].current_level;
            if (val > global_max) {
                global_max = val;
            }

            // Schedule next level up event
            if (chains[id].current_level < m) {
                int next_lvl = chains[id].current_level + 1;
                ll next_trigger = chains[id].start_p + Q[next_lvl];
                pq.push({next_trigger, id, next_lvl});
            }
        }

        // DP transition: best previous configuration + current contribution - penalty
        dp[i] = global_max - c;

        // Create a new chain starting after day i
        // This chain corresponds to picking a new character starting at day i+1
        chains[i] = {current_P, dp[i], start_level};
        
        // Update global max with the initial state of the new chain
        ll initial_val = dp[i] + start_level;
        if (initial_val > global_max) {
            global_max = initial_val;
        }

        // If the new chain has potential to improve the result, add its next event
        if (start_level < m) {
            if (dp[i] + m > global_max) {
                pq.push({current_P + Q[start_level + 1], i, start_level + 1});
            }
        }
    }

    cout << dp[n] << "\n";
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