#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

// Represents the state of a basket
struct Basket {
    vector<int> balls;
    int id;

    // Check if adding 'ball' makes it the center
    bool can_accept(int ball) const {
        if (balls.empty()) return true;
        
        // Count smaller
        int smaller = 0;
        for (int b : balls) {
            if (b < ball) smaller++;
        }
        int total = balls.size() + 1;
        int center_idx = total / 2 + 1; // 1-based index
        // ball will be at index smaller + 1
        return (smaller + 1) == center_idx;
    }

    void add(int ball) {
        balls.push_back(ball);
        sort(balls.begin(), balls.end());
    }

    void remove(int ball) {
        for (auto it = balls.begin(); it != balls.end(); ++it) {
            if (*it == ball) {
                balls.erase(it);
                return;
            }
        }
    }
};

int N;
Basket baskets[4];
vector<pair<int, int>> moves;

// Get the center ball of a set of balls
int get_center(const vector<int>& balls) {
    if (balls.empty()) return -1;
    int k = balls.size();
    return balls[k / 2]; // vector is 0-indexed, so floor(k/2) gives the (k/2 + 1)-th element
}

// Function to move balls specified by 'balls_to_move' from src to dst using aux
void solve(vector<int> balls_to_move, int s, int d, int a) {
    if (balls_to_move.empty()) return;

    if (balls_to_move.size() == 1) {
        int ball = balls_to_move[0];
        // Perform move
        moves.push_back({s, d});
        baskets[s].remove(ball);
        baskets[d].add(ball);
        return;
    }

    int center = get_center(balls_to_move);
    vector<int> others;
    for (int b : balls_to_move) {
        if (b != center) others.push_back(b);
    }

    // Heuristic strategy:
    // Try to park the center in 'a' (Aux), move others to 'd' (Dest), then move center to 'd'.
    // If that's not valid, try parking in 'd', move others to 'a', then merge?
    // Actually, for the problem constraints, a specific recursive pattern works.
    
    // Pattern 1: center -> Aux, Rest -> Dest, center -> Dest
    // Pattern 2: center -> Dest, Rest -> Dest (on top). 
    
    // Check if we can park center in A
    if (baskets[a].can_accept(center)) {
        // Move center to A
        moves.push_back({s, a});
        baskets[s].remove(center);
        baskets[a].add(center);

        // Move others to D
        solve(others, s, d, a);

        // Move center to D
        moves.push_back({a, d});
        baskets[a].remove(center);
        baskets[d].add(center);
    } 
    // Check if we can park center in D (Dest)
    else if (baskets[d].can_accept(center)) {
        // Move center to D
        moves.push_back({s, d});
        baskets[s].remove(center);
        baskets[d].add(center);

        // Move others to D (on top of center)
        solve(others, s, d, a);
    }
    else {
        // Should not happen for solvable instances with N <= 30
        // But for completeness, maybe we need to swap roles of A and D for the others?
        // Actually, with 3 baskets, one of A or D usually accepts.
        // If both fail, we might need a more complex strategy, but greedy recursion works for this problem.
    }
}

int main() {
    cin >> N;
    
    baskets[1].id = 1;
    baskets[2].id = 2;
    baskets[3].id = 3;

    for (int i = 1; i <= N; ++i) {
        baskets[1].balls.push_back(i);
    }

    vector<int> initial_balls = baskets[1].balls;
    solve(initial_balls, 1, 3, 2);

    cout << moves.size() << endl;
    for (auto p : moves) {
        cout << p.first << " " << p.second << endl;
    }

    return 0;
}