#include <bits/stdc++.h>
using namespace std;

struct State {
    int x;
    bool last_lie;
};

int main() {
    int n;
    scanf("%d", &n);
    int num_bits = 0;
    for (int i = 0; (1 << i) <= n; i++) {
        num_bits = i + 1;
    }
    vector<int> received_bit(num_bits);
    for (int i = 0; i < num_bits; i++) {
        vector<int> S;
        for (int j = 1; j <= n; j++) {
            if ((j & (1 << i)) != 0) {
                S.push_back(j);
            }
        }
        printf("? %d", (int)S.size());
        for (int num : S) {
            printf(" %d", num);
        }
        printf("\n");
        fflush(stdout);
        char buf[10];
        scanf("%s", buf);
        string ans = buf;
        received_bit[i] = (ans == "YES" ? 1 : 0);
    }
    vector<State> init_poss;
    int max_m = 1 << num_bits;
    for (int m = 0; m < max_m; m++) {
        if ((m & (m << 1)) != 0) continue;
        int x = 0;
        for (int bitpos = 0; bitpos < num_bits; bitpos++) {
            int flip = (m & (1 << bitpos)) ? 1 : 0;
            int true_b = received_bit[bitpos] ^ flip;
            x += true_b << bitpos;
        }
        if (x >= 1 && x <= n) {
            bool last_lie = (m & (1 << (num_bits - 1))) != 0;
            init_poss.push_back({x, last_lie});
        }
    }
    vector<State> curr = init_poss;
    int queries_used = num_bits;
    while (curr.size() > 2 && queries_used < 53) {
        vector<State> zero_s, one_s;
        for (const auto& st : curr) {
            if (st.last_lie) {
                one_s.push_back(st);
            } else {
                zero_s.push_back(st);
            }
        }
        vector<int> in_S;
        bool is_boosting = one_s.empty();
        if (is_boosting) {
            int tot = zero_s.size();
            int h = tot / 2;
            for (int i = 0; i < h; i++) {
                in_S.push_back(zero_s[i].x);
            }
        } else {
            int zsz = one_s.size();
            int h = zsz / 2;
            for (int i = 0; i < h; i++) {
                in_S.push_back(one_s[i].x);
            }
            for (const auto& st : zero_s) {
                in_S.push_back(st.x);
            }
        }
        if (in_S.empty() && !curr.empty()) {
            in_S.push_back(curr[0].x);
        }
        printf("? %d", (int)in_S.size());
        for (int num : in_S) {
            printf(" %d", num);
        }
        printf("\n");
        fflush(stdout);
        char buf[10];
        scanf("%s", buf);
        string ans_str = buf;
        bool received_yes = (ans_str == "YES");
        set<int> in_S_set(in_S.begin(), in_S.end());
        vector<State> nextt;
        for (const auto& st : curr) {
            bool true_ans = in_S_set.count(st.x) > 0;
            bool implied_lie = (true_ans != received_yes);
            if (st.last_lie && implied_lie) continue;
            nextt.push_back({st.x, implied_lie});
        }
        curr = nextt;
        queries_used++;
    }
    if (curr.empty()) {
        printf("! 1\n");
        fflush(stdout);
        return 0;
    }
    if (curr.size() == 1) {
        printf("! %d\n", curr[0].x);
        fflush(stdout);
        char buf[10];
        scanf("%s", buf);
        return 0;
    } else {
        printf("! %d\n", curr[0].x);
        fflush(stdout);
        char buf[10];
        scanf("%s", buf);
        string res = buf;
        if (res == ":)") return 0;
        printf("! %d\n", curr[1].x);
        fflush(stdout);
        scanf("%s", buf);
        return 0;
    }
    return 0;
}