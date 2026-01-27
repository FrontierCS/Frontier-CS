#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, d;
};

int n;
vector<int> a;
vector<int> posVal;
vector<Op> ops;

// Rotate [l..l+3] right: [v0,v1,v2,v3] -> [v3,v0,v1,v2]
void rotateRight4(int l) {
    int r = l + 3;
    int v0 = a[l], v1 = a[l + 1], v2 = a[l + 2], v3 = a[l + 3];
    a[l] = v3; a[l + 1] = v0; a[l + 2] = v1; a[l + 3] = v2;
    posVal[v3] = l;
    posVal[v0] = l + 1;
    posVal[v1] = l + 2;
    posVal[v2] = l + 3;
}

// Rotate [l..l+3] left: [v0,v1,v2,v3] -> [v1,v2,v3,v0]
void rotateLeft4(int l) {
    int r = l + 3;
    int v0 = a[l], v1 = a[l + 1], v2 = a[l + 2], v3 = a[l + 3];
    a[l] = v1; a[l + 1] = v2; a[l + 2] = v3; a[l + 3] = v0;
    posVal[v1] = l;
    posVal[v2] = l + 1;
    posVal[v3] = l + 2;
    posVal[v0] = l + 3;
}

// BFS structures for last 5 positions
using Arr5 = array<int,5>;
vector<Arr5> bfsStates;
map<Arr5,int> bfsId;
vector<int> bfsParent;
vector<int> bfsOp;

// Build BFS on permutations of 5 elements using 4 operations:
// 0: left rotate [0..3]
// 1: right rotate [0..3]
// 2: left rotate [1..4]
// 3: right rotate [1..4]
void buildBFS() {
    if (!bfsStates.empty()) return; // already built

    Arr5 start = {0,1,2,3,4};
    queue<int> q;

    bfsStates.push_back(start);
    bfsId[start] = 0;
    bfsParent.push_back(0);
    bfsOp.push_back(-1);
    q.push(0);

    while (!q.empty()) {
        int u = q.front(); q.pop();
        Arr5 cur = bfsStates[u];
        for (int op = 0; op < 4; ++op) {
            Arr5 nxt = cur;
            switch (op) {
                case 0: { // left [0..3]
                    int t = nxt[0];
                    nxt[0] = nxt[1];
                    nxt[1] = nxt[2];
                    nxt[2] = nxt[3];
                    nxt[3] = t;
                    break;
                }
                case 1: { // right [0..3]
                    int t = nxt[3];
                    nxt[3] = nxt[2];
                    nxt[2] = nxt[1];
                    nxt[1] = nxt[0];
                    nxt[0] = t;
                    break;
                }
                case 2: { // left [1..4]
                    int t = nxt[1];
                    nxt[1] = nxt[2];
                    nxt[2] = nxt[3];
                    nxt[3] = nxt[4];
                    nxt[4] = t;
                    break;
                }
                case 3: { // right [1..4]
                    int t = nxt[4];
                    nxt[4] = nxt[3];
                    nxt[3] = nxt[2];
                    nxt[2] = nxt[1];
                    nxt[1] = t;
                    break;
                }
            }
            auto it = bfsId.find(nxt);
            if (it == bfsId.end()) {
                int vid = (int)bfsStates.size();
                bfsStates.push_back(nxt);
                bfsId[nxt] = vid;
                bfsParent.push_back(u);
                bfsOp.push_back(op);
                q.push(vid);
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    a.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    // n == 1: trivial
    if (n == 1) {
        cout << 1 << "\n";
        cout << 0 << "\n";
        return 0;
    }

    // Small n: use x = 2 and bubble sort
    if (n <= 4) {
        int x = 2;
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j < n; ++j) {
                if (a[j] > a[j + 1]) {
                    swap(a[j], a[j + 1]);
                    ops.push_back({j, j + 1, 0}); // length-2 rotation (swap)
                }
            }
        }
        cout << x << "\n";
        cout << (int)ops.size() << "\n";
        for (auto &op : ops) {
            cout << op.l << " " << op.r << " " << op.d << "\n";
        }
        return 0;
    }

    // n >= 5: use x = 4 strategy
    int x = 4;
    posVal.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) posVal[a[i]] = i;

    // Place values 1..n-5 at positions 1..n-5
    for (int i = 1; i <= n - 5; ++i) {
        int v = i;
        int p = posVal[v];
        // Move v left by steps of 3 using right rotations on [p-3..p]
        while (p - i >= 3) {
            int l = p - 3;
            rotateRight4(l);
            ops.push_back({l, l + 3, 1});
            p -= 3;
        }
        int d = p - i;
        if (d == 2) {
            // Two left rotations on [i..i+3]
            rotateLeft4(i);
            ops.push_back({i, i + 3, 0});
            rotateLeft4(i);
            ops.push_back({i, i + 3, 0});
        } else if (d == 1) {
            // One left rotation on [i..i+3]
            rotateLeft4(i);
            ops.push_back({i, i + 3, 0});
        }
    }

    // Sort last 5 positions using BFS precomputed scheme
    buildBFS();
    int base = n - 4; // positions base..base+4
    Arr5 curState;
    for (int k = 0; k < 5; ++k) {
        curState[k] = a[base + k] - base; // values are base..base+4 -> 0..4
    }

    int sid = bfsId[curState];
    vector<int> opCodes;
    int vId = sid;
    while (vId != 0) {
        int pId = bfsParent[vId];
        int op = bfsOp[vId];
        int inv;
        if (op == 0) inv = 1;
        else if (op == 1) inv = 0;
        else if (op == 2) inv = 3;
        else inv = 2;
        opCodes.push_back(inv);
        vId = pId;
    }

    // Apply operations from current state to sorted state
    for (int code : opCodes) {
        if (code == 0) { // left [base..base+3]
            int l = base;
            rotateLeft4(l);
            ops.push_back({l, l + 3, 0});
        } else if (code == 1) { // right [base..base+3]
            int l = base;
            rotateRight4(l);
            ops.push_back({l, l + 3, 1});
        } else if (code == 2) { // left [base+1..base+4]
            int l = base + 1;
            rotateLeft4(l);
            ops.push_back({l, l + 3, 0});
        } else { // code == 3, right [base+1..base+4]
            int l = base + 1;
            rotateRight4(l);
            ops.push_back({l, l + 3, 1});
        }
    }

    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }
    return 0;
}