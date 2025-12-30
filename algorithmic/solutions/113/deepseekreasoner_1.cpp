#include <bits/stdc++.h>
using namespace std;

typedef uint64_t StateCode;

struct State {
    vector<int> baskets[3];
    StateCode code;
    State(int N) {
        for (int i = 1; i <= N; i++) {
            baskets[0].push_back(i);
        }
        code = computeCode(N);
    }
    State(const State& other) {
        for (int i = 0; i < 3; i++) {
            baskets[i] = other.baskets[i];
        }
        code = other.code;
    }
    StateCode computeCode(int N) {
        StateCode c = 0;
        for (int b = 0; b < 3; b++) {
            for (int ball : baskets[b]) {
                int idx = ball - 1;
                c |= ((StateCode)b << (2*idx));
            }
        }
        return c;
    }
};

int getCenterBall(const vector<int>& v) {
    int n = v.size();
    if (n == 0) return -1;
    return v[n/2];
}

bool canMove(int y, const vector<int>& target) {
    int n = target.size();
    int required_pos = (n+1)/2;
    int pos = lower_bound(target.begin(), target.end(), y) - target.begin();
    return pos == required_pos;
}

int main() {
    int N;
    cin >> N;

    State start(N);
    StateCode goalCode = 0;
    for (int i = 1; i <= N; i++) {
        goalCode |= ((StateCode)2 << (2*(i-1)));
    }

    if (start.code == goalCode) {
        cout << 0 << endl;
        return 0;
    }

    queue<State> q;
    q.push(start);

    unordered_map<StateCode, pair<StateCode, pair<int,int>>> parent;
    parent[start.code] = {0, {-1,-1}};

    State finalState = start;
    bool found = false;

    while (!q.empty()) {
        State cur = q.front(); q.pop();

        if (cur.code == goalCode) {
            finalState = cur;
            found = true;
            break;
        }

        for (int a = 0; a < 3; a++) {
            if (cur.baskets[a].empty()) continue;
            int y = getCenterBall(cur.baskets[a]);
            for (int b = 0; b < 3; b++) {
                if (b == a) continue;
                if (canMove(y, cur.baskets[b])) {
                    State next = cur;
                    auto& ba = next.baskets[a];
                    ba.erase(find(ba.begin(), ba.end(), y));
                    auto& bb = next.baskets[b];
                    int pos = lower_bound(bb.begin(), bb.end(), y) - bb.begin();
                    bb.insert(bb.begin() + pos, y);
                    next.code = next.computeCode(N);
                    if (parent.find(next.code) == parent.end()) {
                        parent[next.code] = {cur.code, {a+1, b+1}};
                        q.push(next);
                    }
                }
            }
        }
    }

    if (!found) {
        return 0;
    }

    vector<pair<int,int>> moves;
    StateCode curCode = finalState.code;
    while (parent[curCode].second.first != -1) {
        moves.push_back(parent[curCode].second);
        curCode = parent[curCode].first;
    }
    reverse(moves.begin(), moves.end());

    cout << moves.size() << endl;
    for (auto& m : moves) {
        cout << m.first << " " << m.second << endl;
    }

    return 0;
}