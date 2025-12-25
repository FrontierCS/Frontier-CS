#include <iostream>
#include <vector>
#include <queue>
#include <string>
#include <algorithm>
#include <cassert>

using namespace std;

int N, R;
vector<int> U, V;
vector<int> parent; // for each slot i, the slot that uses switch i as input, or -1
vector<char> type; // '&' or '|'
vector<int> config; // temporary configuration for building query

void set_output(int j, int val) {
    if (config[j] != -1) return; // already set, should be consistent
    if (j >= N) {
        config[j] = val; // leaf switch: output = state
    } else {
        // internal switch (output of a slot)
        config[j] = 0; // set switch OFF so output = slot output
        // force slot j's output to val by setting both children to val
        set_output(U[j], val);
        set_output(V[j], val);
    }
}

string build_query(int i) {
    // i is the slot to test
    config.assign(2*N+1, -1); // -1 means not set yet

    // Step 1: set switch i OFF
    config[i] = 0;

    // Step 2: set children to 0 and 1 respectively
    set_output(U[i], 0);
    set_output(V[i], 1);

    // Step 3: handle ancestors to make them buffer the path
    int cur = i;
    while (parent[cur] != -1) {
        int p = parent[cur];
        // determine the other child of p (not cur)
        int other;
        if (U[p] == cur) other = V[p];
        else other = U[p];
        // based on known type of p, set the other child to 1 if AND, 0 if OR
        int needed = (type[p] == '&') ? 1 : 0;
        set_output(other, needed);
        // set switch p OFF
        config[p] = 0;
        cur = p;
    }
    // ensure switch 0 is OFF (root output)
    if (config[0] == -1) config[0] = 0;

    // Step 4: set all remaining switches to OFF
    for (int j = 0; j <= 2*N; ++j) {
        if (config[j] == -1) config[j] = 0;
    }

    // convert to string
    string s(2*N+1, '0');
    for (int j = 0; j <= 2*N; ++j) {
        s[j] = config[j] + '0';
    }
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> N >> R;
    U.resize(N);
    V.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> U[i] >> V[i];
    }

    // compute parent of each slot
    parent.assign(N, -1);
    for (int i = 0; i < N; ++i) {
        if (U[i] < N) parent[U[i]] = i;
        if (V[i] < N) parent[V[i]] = i;
    }

    type.assign(N, '?');

    queue<int> q;
    q.push(0); // root slot

    while (!q.empty()) {
        int i = q.front(); q.pop();
        string query_str = build_query(i);
        cout << "? " << query_str << endl;
        int output;
        cin >> output;
        type[i] = (output == 0) ? '&' : '|';
        // enqueue child slots that haven't been processed
        if (U[i] < N && type[U[i]] == '?') q.push(U[i]);
        if (V[i] < N && type[V[i]] == '?') q.push(V[i]);
    }

    string ans(N, ' ');
    for (int i = 0; i < N; ++i) {
        ans[i] = type[i];
    }
    cout << "! " << ans << endl;

    return 0;
}