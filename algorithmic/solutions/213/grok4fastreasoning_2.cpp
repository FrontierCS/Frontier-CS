#include <bits/stdc++.h>
using namespace std;

void gen_perms(vector<int>& cur, int pos, vector<vector<int>>& all_perms, map<vector<int>, int>& perm_to_id) {
    if (pos == 5) {
        int id = all_perms.size();
        all_perms.push_back(cur);
        perm_to_id[cur] = id;
        return;
    }
    for (int i = pos; i < 5; ++i) {
        swap(cur[pos], cur[i]);
        gen_perms(cur, pos + 1, all_perms, perm_to_id);
        swap(cur[pos], cur[i]);
    }
}

int main() {
    int n;
    cin >> n;
    vector<int> arr(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> arr[i];
    }

    // Precompute permutations for BFS
    vector<vector<int>> all_perms;
    map<vector<int>, int> perm_to_id;
    vector<int> tmp(5);
    for (int i = 0; i < 5; ++i) tmp[i] = i;
    gen_perms(tmp, 0, all_perms, perm_to_id);

    // BFS
    int target = perm_to_id[{0, 1, 2, 3, 4}];
    vector<int> parent(120, -1);
    vector<int> op_to(120, -1);
    vector<int> distance(120, -1);
    queue<int> q;
    q.push(target);
    distance[target] = 0;
    while (!q.empty()) {
        int sid = q.front();
        q.pop();
        vector<int> state = all_perms[sid];
        for (int w = 0; w < 2; ++w) {
            for (int dir = 0; dir < 2; ++dir) {
                vector<int> nstate = state;
                int aa = (w == 0 ? 0 : 1);
                int bb = aa + 3;
                if (dir == 0) { // left
                    int temp = nstate[aa];
                    for (int kk = aa; kk < bb; ++kk) nstate[kk] = nstate[kk + 1];
                    nstate[bb] = temp;
                } else { // right
                    int temp = nstate[bb];
                    for (int kk = bb; kk > aa; --kk) nstate[kk] = nstate[kk - 1];
                    nstate[aa] = temp;
                }
                auto it = perm_to_id.find(nstate);
                if (it != perm_to_id.end()) {
                    int nid = it->second;
                    if (distance[nid] == -1) {
                        distance[nid] = distance[sid] + 1;
                        parent[nid] = sid;
                        op_to[nid] = w * 2 + dir;
                        q.push(nid);
                    }
                }
            }
        }
    }

    vector<tuple<int, int, int>> ops;
    int xx = (n <= 6 ? 2 : 4);
    if (xx == 2) {
        for (int i = 1; i < n; ++i) {
            int j = i;
            while (arr[j] != i) ++j;
            for (int k = j; k > i; --k) {
                ops.emplace_back(k - 1, k, 1);
                swap(arr[k - 1], arr[k]);
            }
        }
    } else {
        // x=4, n>=7
        for (int i = 1; i <= n - 3; ++i) {
            int j = i;
            while (arr[j] != i) ++j;
            int dd = j - i;
            // jumps
            while (dd >= 3) {
                int l = j - 3;
                ops.emplace_back(l, l + 3, 1); // right
                // simulate right
                int temp = arr[l + 3];
                for (int kk = l + 3; kk > l; --kk) arr[kk] = arr[kk - 1];
                arr[l] = temp;
                j = l;
                dd = j - i;
            }
            // final left shifts
            int num_shifts = dd;
            for (int t = 0; t < num_shifts; ++t) {
                ops.emplace_back(i, i + 3, 0); // left
                // simulate left
                int temp = arr[i];
                for (int kk = i; kk < i + 3; ++kk) arr[kk] = arr[kk + 1];
                arr[i + 3] = temp;
            }
        }
        // now handle last 3: positions n-2 to n
        int base_pos = n - 4;
        int base_num = n - 4;
        vector<int> cur_state(5);
        for (int kk = 0; kk < 5; ++kk) {
            int pos = base_pos + kk;
            cur_state[kk] = arr[pos] - base_num;
        }
        int cid = perm_to_id[cur_state];
        // reconstruct
        vector<int> opseq;
        int current = cid;
        while (current != target) {
            int prevv = parent[current];
            int oop = op_to[current];
            int inv_d = 1 - (oop % 2);
            int inv_w = oop / 2;
            int inv_op = inv_w * 2 + inv_d;
            opseq.push_back(inv_op);
            current = prevv;
        }
        reverse(opseq.begin(), opseq.end());
        // apply
        for (int iop : opseq) {
            int w = iop / 2;
            int d = iop % 2;
            int l, r;
            if (w == 0) {
                l = base_pos;
                r = base_pos + 3;
            } else {
                l = base_pos + 1;
                r = base_pos + 4;
            }
            ops.emplace_back(l, r, d);
            // simulate
            if (d == 0) { // left
                int temp = arr[l];
                for (int kk = l; kk < r; ++kk) arr[kk] = arr[kk + 1];
                arr[r] = temp;
            } else { // right
                int temp = arr[r];
                for (int kk = r; kk > l; --kk) arr[kk] = arr[kk - 1];
                arr[l] = temp;
            }
        }
    }

    cout << xx << " " << ops.size() << endl;
    for (auto [l, r, d] : ops) {
        cout << l << " " << r << " " << d << endl;
    }
    return 0;
}