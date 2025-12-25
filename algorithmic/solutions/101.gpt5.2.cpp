#include <bits/stdc++.h>
using namespace std;

static int N, Rv;
static vector<int> U, V;
static vector<int> parentSlot;   // for each switch-node j: parent slot index p such that j is U[p] or V[p], -1 for root (0)
static vector<unsigned char> sideInParent; // 0 if j==U[parent], 1 if j==V[parent]
static vector<char> gateType;    // '&' or '|', for slots 0..N-1

static int ask(const string &s) {
    cout << "? " << s << endl;
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans < 0) exit(0);
    return ans;
}

static inline void assignConst(int node, int val, string &s) {
    // Force switch-node 'node' output to constant val (0/1), regardless of unknown gates in its subtree:
    // - If node is a leaf (>=N): set its switch state to val
    // - If internal (<N): set its switch state to val, and force both children outputs to 0
    vector<pair<int,int>> st;
    st.reserve(64);
    st.push_back({node, val});
    while (!st.empty()) {
        auto [x, v] = st.back();
        st.pop_back();
        s[x] = char('0' + v);
        if (x < N) {
            st.push_back({U[x], 0});
            st.push_back({V[x], 0});
        }
    }
}

static string buildQueryForGate(int i) {
    int M = 2 * N + 1;
    string s(M, '0');

    // Ensure no inversion on switch i itself
    s[i] = '0';

    // Set i's inputs to (0,1) so AND->0, OR->1
    assignConst(U[i], 0, s);
    assignConst(V[i], 1, s);

    if (i != 0) {
        int cur = i;
        while (cur != 0) {
            int p = parentSlot[cur];
            // p must be in [0..N-1], and already known when processing i in increasing order
            s[p] = '0'; // no inversion at p

            int sibling = (sideInParent[cur] == 0) ? V[p] : U[p];
            int neutral = (gateType[p] == '&') ? 1 : 0;
            assignConst(sibling, neutral, s);

            cur = p;
        }
    }

    s[0] = '0'; // no inversion at root switch
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> Rv;
    U.resize(N);
    V.resize(N);
    int M = 2 * N + 1;

    parentSlot.assign(M, -1);
    sideInParent.assign(M, 0);

    for (int i = 0; i < N; i++) {
        cin >> U[i] >> V[i];
        parentSlot[U[i]] = i;
        sideInParent[U[i]] = 0;
        parentSlot[V[i]] = i;
        sideInParent[V[i]] = 1;
    }

    gateType.assign(N, '?');

    for (int i = 0; i < N; i++) {
        string q = buildQueryForGate(i);
        int out = ask(q);
        gateType[i] = (out == 0 ? '&' : '|');
    }

    cout << "! ";
    for (int i = 0; i < N; i++) cout << gateType[i];
    cout << endl;
    cout.flush();

    return 0;
}