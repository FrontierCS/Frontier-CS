#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int n;
vector<int> cards[105];
int cnt[105][105]; // cnt[player][card_value]

struct Op {
    vector<int> moves;
};

vector<Op> history_ops;

// Check if a specific player is solid (all cards are equal to player index)
bool is_solid(int p, const int current_cnt[105][105]) {
    return current_cnt[p][p] == n;
}

// Check if all players are solid
bool check_done(const int current_cnt[105][105]) {
    for (int i = 1; i <= n; ++i) {
        if (!is_solid(i, current_cnt)) return false;
    }
    return true;
}

// Helper to determine moves based on a penalty for dangerous feeds
vector<int> get_moves(bool use_safety_penalty) {
    vector<int> moves(n + 1);
    // Snapshot of solid counts for safety check
    vector<int> solid_counts(n + 1);
    for(int i=1; i<=n; ++i) solid_counts[i] = cnt[i][i];

    for (int i = 1; i <= n; ++i) {
        int next_p = (i % n) + 1;
        
        // Find unique card values held by player i
        vector<int> distinct_cards;
        for (int c : cards[i]) {
            bool found = false;
            for (int dc : distinct_cards) if (dc == c) found = true;
            if (!found) distinct_cards.push_back(c);
        }

        int best_card = -1;
        int best_score = -999999;

        for (int c : distinct_cards) {
            int score = 0;
            
            if (c == i) {
                score = -100; // Prefer not to pass correct card
            } else {
                if (c == next_p) {
                    // Pass to target
                    if (use_safety_penalty && solid_counts[next_p] >= n - 1) {
                        score = -200; // Danger: creates solid player prematurely
                    } else {
                        score = 10; // Good: feeds target
                    }
                } else {
                    score = 5; // Neutral wrong card (moves card but not to immediate target)
                }
            }
            
            if (score > best_score) {
                best_score = score;
                best_card = c;
            }
        }
        moves[i] = best_card;
    }
    return moves;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < n; ++j) {
            int c;
            cin >> c;
            cards[i].push_back(c);
            cnt[i][c]++;
        }
    }

    int max_ops = n * (n - 1);
    
    if (check_done(cnt)) {
        cout << 0 << "\n";
        return 0;
    }

    while (history_ops.size() < max_ops) {
        // Try Aggressive Strategy (no safety penalty) first
        // If it solves the problem in 1 step, take it.
        vector<int> agg_moves = get_moves(false);
        
        // Simulate Aggressive
        int temp_cnt[105][105];
        for(int i=1; i<=n; ++i) for(int j=1; j<=n; ++j) temp_cnt[i][j] = cnt[i][j];
        
        for (int i = 1; i <= n; ++i) {
            int c = agg_moves[i];
            temp_cnt[i][c]--;
            int next_p = (i % n) + 1;
            temp_cnt[next_p][c]++;
        }

        if (check_done(temp_cnt)) {
            history_ops.push_back({vector<int>(agg_moves.begin() + 1, agg_moves.end())});
            break;
        }

        // If aggressive doesn't finish, use Safe Strategy
        vector<int> safe_moves = get_moves(true);
        history_ops.push_back({vector<int>(safe_moves.begin() + 1, safe_moves.end())});
        
        // Apply Safe moves
        // Remove cards
        for (int i = 1; i <= n; ++i) {
            int c = safe_moves[i];
            auto it = find(cards[i].begin(), cards[i].end(), c);
            cards[i].erase(it);
            cnt[i][c]--;
        }

        // Add cards
        for (int i = 1; i <= n; ++i) {
            int next_p = (i % n) + 1;
            int c = safe_moves[i];
            cards[next_p].push_back(c);
            cnt[next_p][c]++;
        }

        if (check_done(cnt)) break;
    }

    cout << history_ops.size() << "\n";
    for (const auto& op : history_ops) {
        for (int i = 0; i < n; ++i) {
            cout << op.moves[i] << (i == n - 1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}