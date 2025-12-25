#include <iostream>
#include <vector>
#include <queue>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <stack>

using namespace std;

// State representation: each ball (0..N-1) uses 2 bits to store basket (0,1,2)
using State = unsigned long long;

// Get basket of ball i from state
inline int getBasket(State state, int i) {
    return (state >> (2*i)) & 3;
}

// Set basket of ball i in state
inline State setBasket(State state, int i, int basket) {
    state &= ~(3ULL << (2*i));
    state |= (static_cast<State>(basket) << (2*i));
    return state;
}

// Compute the sorted list of balls in a given basket for a state
vector<int> getBallsInBasket(State state, int basket, int N) {
    vector<int> balls;
    for (int i = 0; i < N; ++i) {
        if (getBasket(state, i) == basket) {
            balls.push_back(i);
        }
    }
    return balls; // already sorted because i increases
}

// Find the center ball of a basket. Assumes basket is non-empty.
int getCenterBall(const vector<int>& balls) {
    int sz = balls.size();
    // center index (0-indexed) = floor(sz/2)
    return balls[sz / 2];
}

// Check if moving ball 'c' from basket a to basket b is valid.
bool isValidMove(State state, int a, int b, int c, int N) {
    // Get balls in destination basket b
    vector<int> destBalls = getBallsInBasket(state, b, N);
    int k = destBalls.size();
    // Count how many balls in b are less than c
    int left = 0;
    for (int ball : destBalls) {
        if (ball < c) left++;
        else break; // since balls are sorted
    }
    // Condition: left must be equal to floor((k+1)/2)
    return left == ((k + 1) / 2);
}

// Perform the move: return new state after moving center of basket a to basket b
State performMove(State state, int a, int b, int N) {
    vector<int> srcBalls = getBallsInBasket(state, a, N);
    int c = getCenterBall(srcBalls);
    // Update state: remove c from a, add to b
    state = setBasket(state, c, b);
    return state;
}

// Encode a move (a,b) as an integer: a*10 + b (a,b are 0-based)
int encodeMove(int a, int b) {
    return a * 10 + b;
}

// Decode move into a and b (0-based)
pair<int,int> decodeMove(int code) {
    return {code / 10, code % 10};
}

int main() {
    int N;
    cin >> N;

    // Initial state: all balls in basket 0 (basket 1 in problem)
    State start = 0;
    for (int i = 0; i < N; ++i) {
        start = setBasket(start, i, 0);
    }

    // Goal state: all balls in basket 2 (basket 3 in problem)
    State goal = 0;
    for (int i = 0; i < N; ++i) {
        goal = setBasket(goal, i, 2);
    }

    // BFS
    unordered_map<State, pair<State, int>> parent; // state -> (parent_state, encoded_move)
    unordered_set<State> visited;
    queue<State> q;

    q.push(start);
    visited.insert(start);
    parent[start] = {start, -1}; // start has no parent

    bool found = false;
    while (!q.empty()) {
        State cur = q.front(); q.pop();

        if (cur == goal) {
            found = true;
            break;
        }

        // For each pair of baskets (a,b) with a != b
        for (int a = 0; a < 3; ++a) {
            for (int b = 0; b < 3; ++b) {
                if (a == b) continue;
                vector<int> srcBalls = getBallsInBasket(cur, a, N);
                if (srcBalls.empty()) continue;
                int c = getCenterBall(srcBalls);
                // Check if move is valid
                if (isValidMove(cur, a, b, c, N)) {
                    State next = performMove(cur, a, b, N);
                    if (visited.find(next) == visited.end()) {
                        visited.insert(next);
                        parent[next] = {cur, encodeMove(a,b)};
                        q.push(next);
                    }
                }
            }
        }
    }

    if (!found) {
        // According to problem statement, a solution always exists.
        // This should not happen for N <= 30.
        return 0;
    }

    // Reconstruct path
    stack<pair<int,int>> moves; // store moves (a,b) as 0-based
    State cur = goal;
    while (cur != start) {
        auto [prev, moveCode] = parent[cur];
        auto [a,b] = decodeMove(moveCode);
        moves.push({a,b});
        cur = prev;
    }

    // Output
    cout << moves.size() << endl;
    while (!moves.empty()) {
        auto [a,b] = moves.top(); moves.pop();
        // Convert to 1-based basket numbers
        cout << a+1 << " " << b+1 << endl;
    }

    return 0;
}