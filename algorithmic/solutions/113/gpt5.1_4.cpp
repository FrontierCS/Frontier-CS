#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    const int MAXN = 30;
    vector<ll> pow3(N);
    pow3[0] = 1;
    for (int i = 1; i < N; ++i) pow3[i] = pow3[i - 1] * 3LL;

    ll initial = 0;
    ll goal = 0;
    for (int i = 0; i < N; ++i) goal += 2LL * pow3[i]; // all balls in basket 3 (digit 2)

    vector<ll> states;
    vector<int> parent;
    vector<unsigned char> mv_src, mv_dst;

    states.reserve(1000000);
    parent.reserve(1000000);
    mv_src.reserve(1000000);
    mv_dst.reserve(1000000);

    unordered_map<ll, int> mp;
    mp.reserve(1000000);
    mp.max_load_factor(0.7f);

    states.push_back(initial);
    parent.push_back(-1);
    mv_src.push_back(0);
    mv_dst.push_back(0);
    mp[initial] = 0;

    queue<int> q;
    q.push(0);

    vector<int> pos(MAXN);
    array<int, 3> cnt;

    int goal_id = -1;
    bool found = false;

    while (!q.empty() && !found) {
        int id = q.front(); q.pop();
        ll code = states[id];

        if (code == goal) {
            goal_id = id;
            found = true;
            break;
        }

        // decode state into pos[] and cnt[]
        ll tmp = code;
        cnt = {0, 0, 0};
        for (int i = 0; i < N; ++i) {
            int b = (int)(tmp % 3LL);
            tmp /= 3LL;
            pos[i] = b;
            cnt[b]++;
        }

        for (int src = 0; src < 3; ++src) {
            int s_cnt = cnt[src];
            if (s_cnt == 0) continue;

            int needRank;
            if (s_cnt % 2 == 1) needRank = (s_cnt + 1) / 2;
            else needRank = s_cnt / 2 + 1;

            int centerPos = -1;
            int seen = 0;
            for (int i = 0; i < N; ++i) {
                if (pos[i] == src) {
                    ++seen;
                    if (seen == needRank) {
                        centerPos = i;
                        break;
                    }
                }
            }
            if (centerPos == -1) continue; // should not happen

            for (int dest = 0; dest < 3; ++dest) {
                if (dest == src) continue;

                int sd = cnt[dest];
                int sp = sd + 1;
                int centerRank;
                if (sp % 2 == 1) centerRank = (sp + 1) / 2;
                else centerRank = sp / 2 + 1;

                int L = 0;
                for (int i = 0; i < centerPos; ++i) {
                    if (pos[i] == dest) ++L;
                }
                int rank = L + 1;
                if (rank != centerRank) continue;

                ll new_code = code + (ll)(dest - src) * pow3[centerPos];

                auto it = mp.find(new_code);
                if (it == mp.end()) {
                    int new_id = (int)states.size();
                    states.push_back(new_code);
                    parent.push_back(id);
                    mv_src.push_back((unsigned char)(src + 1));
                    mv_dst.push_back((unsigned char)(dest + 1));
                    mp.emplace(new_code, new_id);
                    q.push(new_id);
                }
            }
        }
    }

    if (!found) {
        // Should not occur for valid problem instances.
        cout << 0 << '\n';
        return 0;
    }

    vector<pair<int,int>> ops;
    int cur = goal_id;
    while (parent[cur] != -1) {
        ops.push_back({(int)mv_src[cur], (int)mv_dst[cur]});
        cur = parent[cur];
    }
    reverse(ops.begin(), ops.end());

    cout << ops.size() << '\n';
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}