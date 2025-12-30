#include <bits/stdc++.h>
using namespace std;

int N, R;
vector<int> U_, V_;
vector<int> parentGate, parentSide; // parentSide: 0 if this gate is via U, 1 if via V

vector<int> Lnode, Rnode;           // leaf index interval [L, R) for each gate
vector<int> leafOrder;              // map switch index (>=N) -> leaf DFS order
vector<int> leafSwitchByOrder;      // map leaf DFS order -> switch index
int leafCnt = 0;

vector<int> leafAssign;             // assigned value for each DFS leaf index
vector<int> leafStamp;              // stamp to know which query the assignment belongs to
int curStamp = 0;

vector<int> isOrGate;               // 1 if OR, 0 if AND

int totalSwitches;

// DFS to compute leaf order and subtree intervals
void dfs(int g) {
    Lnode[g] = N + 1;
    Rnode[g] = -1;

    int sw = U_[g];
    if (sw < N) {
        dfs(sw);
        Lnode[g] = min(Lnode[g], Lnode[sw]);
        Rnode[g] = max(Rnode[g], Rnode[sw]);
    } else {
        int idx = leafOrder[sw];
        if (idx == -1) {
            idx = leafCnt++;
            leafOrder[sw] = idx;
            leafSwitchByOrder[idx] = sw;
        }
        Lnode[g] = min(Lnode[g], idx);
        Rnode[g] = max(Rnode[g], idx + 1);
    }

    sw = V_[g];
    if (sw < N) {
        dfs(sw);
        Lnode[g] = min(Lnode[g], Lnode[sw]);
        Rnode[g] = max(Rnode[g], Rnode[sw]);
    } else {
        int idx = leafOrder[sw];
        if (idx == -1) {
            idx = leafCnt++;
            leafOrder[sw] = idx;
            leafSwitchByOrder[idx] = sw;
        }
        Lnode[g] = min(Lnode[g], idx);
        Rnode[g] = max(Rnode[g], idx + 1);
    }
}

// Assign all leaves in subtree of given switch index to value val (0/1)
void assignSubtree(int sw, int val) {
    if (sw < N) {
        int l = Lnode[sw], r = Rnode[sw];
        for (int i = l; i < r; ++i) {
            leafAssign[i] = val;
            leafStamp[i] = curStamp;
        }
    } else {
        int idx = leafOrder[sw];
        leafAssign[idx] = val;
        leafStamp[idx] = curStamp;
    }
}

// Send a query and read the result
int ask(const string &s) {
    cout << "? " << s << '\n' << flush;
    int res;
    if (!(cin >> res)) {
        // If judge ends interaction or error occurs
        exit(0);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> R)) {
        return 0;
    }

    U_.resize(N);
    V_.resize(N);
    parentGate.assign(N, -1);
    parentSide.assign(N, -1);

    for (int i = 0; i < N; ++i) {
        cin >> U_[i] >> V_[i];
    }

    // Build parent info
    for (int i = 0; i < N; ++i) {
        int a = U_[i];
        int b = V_[i];
        if (a < N) {
            parentGate[a] = i;
            parentSide[a] = 0;
        }
        if (b < N) {
            parentGate[b] = i;
            parentSide[b] = 1;
        }
    }

    // Prepare for DFS
    Lnode.assign(N, 0);
    Rnode.assign(N, 0);
    leafOrder.assign(2 * N + 1, -1);
    leafSwitchByOrder.assign(N + 1, -1);
    leafCnt = 0;

    dfs(0); // root gate is 0

    totalSwitches = 2 * N + 1;

    leafAssign.assign(leafCnt, 0);
    leafStamp.assign(leafCnt, 0);
    isOrGate.assign(N, -1);

    // Determine gate types in increasing index order
    for (int g = 0; g < N; ++g) {
        ++curStamp;

        // Switch states: initialize all to '0'
        string s(totalSwitches, '0'); // internal switches 0..N-1 are kept 0 (no inversion)

        // Set children of gate g: we choose inputs (0,1)
        assignSubtree(U_[g], 0);
        assignSubtree(V_[g], 1);

        // For each ancestor, set sibling subtree to neutral value
        int node = g;
        while (parentGate[node] != -1) {
            int p = parentGate[node];
            int sibSw = (parentSide[node] == 0) ? V_[p] : U_[p];
            int neutralVal = (isOrGate[p] == 1) ? 0 : 1; // OR: 0, AND: 1
            assignSubtree(sibSw, neutralVal);
            node = p;
        }

        // Convert leaf assignments to switch bits
        for (int i = 0; i < leafCnt; ++i) {
            int sw = leafSwitchByOrder[i];
            int val = (leafStamp[i] == curStamp) ? leafAssign[i] : 0;
            s[sw] = val ? '1' : '0';
        }

        int res = ask(s);
        // Under this assignment, output of switch 0 equals output of gate g with inputs (0,1)
        // If gate is AND, output 0; if OR, output 1.
        isOrGate[g] = (res == 1) ? 1 : 0;
    }

    // Output final answer
    string t(N, '&');
    for (int i = 0; i < N; ++i) {
        if (isOrGate[i]) t[i] = '|';
    }
    cout << "! " << t << '\n' << flush;

    return 0;
}