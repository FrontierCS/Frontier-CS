#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

// Structure to represent the state of baskets
struct State {
    vector<int> baskets[4]; // 1-based indexing for baskets
};

int N;
vector<pair<int, int>> moves;
State currentState;

// Helper to calculate center
int get_center(const vector<int>& b) {
    if (b.empty()) return -1;
    int k = b.size();
    int idx = k / 2; // 0-based index: k/2 corresponds to floor(k/2) + 1 in 1-based
    // But wait, the problem says:
    // If odd (e.g. 3): center is (3+1)/2 = 2nd. 0-based index 1. 3/2 = 1. Correct.
    // If even (e.g. 2): center is larger of two middle. Indices 1, 2. Larger is 2. 0-based index 1. 2/2 = 1. Correct.
    // If 4: middle 2, 3. Larger 3. 0-based index 2. 4/2 = 2. Correct.
    return b[idx];
}

// Helper to check validity of move
bool is_valid(const vector<int>& dest, int val) {
    vector<int> temp = dest;
    temp.push_back(val);
    sort(temp.begin(), temp.end());
    int c = get_center(temp);
    return c == val;
}

// Helper to perform move
void do_move(int u, int v) {
    // Find ball
    int val = get_center(currentState.baskets[u]);
    // Remove
    auto& src = currentState.baskets[u];
    src.erase(find(src.begin(), src.end(), val));
    sort(src.begin(), src.end()); // Keep sorted just in case
    
    // Add
    auto& dst = currentState.baskets[v];
    dst.push_back(val);
    sort(dst.begin(), dst.end());
    
    moves.push_back({u, v});
}

// Find which basket contains val
int find_basket(int val) {
    for (int i = 1; i <= 3; ++i) {
        for (int x : currentState.baskets[i]) {
            if (x == val) return i;
        }
    }
    return -1;
}

// Forward declaration
void move_ball(int val, int target_basket);

// Move the center of basket b_idx to target_basket
// If blocked, recursively clear the way
void move_center(int b_idx, int target_basket) {
    int val = get_center(currentState.baskets[b_idx]);
    if (b_idx == target_basket) return;

    if (is_valid(currentState.baskets[target_basket], val)) {
        do_move(b_idx, target_basket);
    } else {
        // Target is blocked. We need to modify target basket.
        // Move the center of target basket to the third basket.
        int other = 6 - b_idx - target_basket;
        move_center(target_basket, other);
        // Retry
        move_center(b_idx, target_basket);
    }
}

// High level function to move a specific ball val to target_basket
void move_ball(int val, int target_basket) {
    int b_idx = find_basket(val);
    if (b_idx == target_basket) return;

    int center = get_center(currentState.baskets[b_idx]);
    if (center == val) {
        // Try to move directly
        if (is_valid(currentState.baskets[target_basket], val)) {
            do_move(b_idx, target_basket);
        } else {
            // Target blocked
            int other = 6 - b_idx - target_basket;
            move_center(target_basket, other);
            move_ball(val, target_basket);
        }
    } else {
        // val is not center, move center away
        int other = 6 - b_idx - target_basket;
        // Optimization: check if moving to 'other' is good?
        // Just move center to 'other'
        move_ball(center, other);
        move_ball(val, target_basket);
    }
}

int main() {
    cin >> N;

    for (int i = 1; i <= N; ++i) {
        currentState.baskets[1].push_back(i);
    }

    // Target sequence construction
    // We need balls to arrive in Basket 3 in a specific order:
    // 1, N, 2, N-1, 3, N-2, ...
    vector<int> target_order;
    int left = 1, right = N;
    while (left <= right) {
        target_order.push_back(left++);
        if (left <= right) target_order.push_back(right--);
    }

    // Execute moves
    for (int val : target_order) {
        move_ball(val, 3);
    }

    cout << moves.size() << endl;
    for (auto p : moves) {
        cout << p.first << " " << p.second << endl;
    }

    return 0;
}