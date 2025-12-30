#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    // Precompute powers of 3 for base-3 encoding
    vector<unsigned long long> pow3(N + 1);
    pow3[0] = 1;
    for (int i = 1; i <= N; ++i) pow3[i] = pow3[i - 1] * 3ULL;

    // Encode state: pos[i] in {0,1,2} (basket 1,2,3) as digit in base 3
    unsigned long long start = 0; // all in basket 1 -> all digits 0
    unsigned long long target = 0;
    for (int i = 0; i < N; ++i) target += 2ULL * pow3[i]; // all in basket 3 -> digit 2

    vector<unsigned long long> codes;
    vector<int> parent;
    vector<unsigned char> moveFrom, moveTo;

    codes.reserve(1000000);
    parent.reserve(1000000);
    moveFrom.reserve(1000000);
    moveTo.reserve(1000000);

    unordered_map<unsigned long long, int> id;
    id.reserve(1000000);
    id.max_load_factor(0.7);

    queue<int> q;

    codes.push_back(start);
    parent.push_back(-1);
    moveFrom.push_back(0);
    moveTo.push_back(0);
    id[start] = 0;
    q.push(0);

    int goal = -1;
    vector<int> pos(N);
    vector<int> bucket[3];

    bool done = false;
    while (!q.empty() && !done) {
        int curIdx = q.front(); q.pop();
        unsigned long long code = codes[curIdx];
        if (code == target) { goal = curIdx; break; }

        unsigned long long temp = code;
        for (int i = 0; i < N; ++i) {
            pos[i] = static_cast<int>(temp % 3ULL);
            temp /= 3ULL;
        }

        for (int b = 0; b < 3; ++b) bucket[b].clear();
        for (int i = 0; i < N; ++i) {
            bucket[pos[i]].push_back(i + 1); // store ball labels (1..N), naturally sorted
        }

        for (int a = 0; a < 3 && !done; ++a) {
            auto &vecA = bucket[a];
            int szA = (int)vecA.size();
            if (szA == 0) continue;

            int centerIndex = szA / 2; // 0-based, works for both even and odd
            int ballLabel = vecA[centerIndex];
            int ballId = ballLabel - 1; // index in pos[], 0-based

            for (int b = 0; b < 3; ++b) {
                if (b == a) continue;
                auto &vecB = bucket[b];
                int t = (int)vecB.size();
                int cntLess = 0;
                for (int y : vecB) if (y < ballLabel) ++cntLess;

                if (cntLess != (t + 1) / 2) continue; // destination center condition

                unsigned long long newCode = code + (long long)(b - a) * pow3[ballId];
                if (id.find(newCode) == id.end()) {
                    int newIdx = (int)codes.size();
                    id[newCode] = newIdx;
                    codes.push_back(newCode);
                    parent.push_back(curIdx);
                    moveFrom.push_back((unsigned char)a);
                    moveTo.push_back((unsigned char)b);
                    if (newCode == target) {
                        goal = newIdx;
                        done = true;
                        break;
                    }
                    q.push(newIdx);
                }
            }
        }
    }

    if (goal == -1) {
        // Should not happen for valid inputs by problem statement
        cout << 0 << '\n';
        return 0;
    }

    vector<pair<int,int>> ops;
    for (int idx = goal; parent[idx] != -1; idx = parent[idx]) {
        ops.push_back({(int)moveFrom[idx] + 1, (int)moveTo[idx] + 1});
    }
    reverse(ops.begin(), ops.end());

    cout << ops.size() << '\n';
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}