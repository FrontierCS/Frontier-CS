#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

vector<ll> get_divisors(ll num) {
    vector<ll> divisors;
    for (ll i = 1; i * i <= num; ++i) {
        if (num % i == 0) {
            divisors.push_back(i);
            if (i != num / i) {
                divisors.push_back(num / i);
            }
        }
    }
    sort(divisors.begin(), divisors.end());
    return divisors;
}

ll compute_expected_c(const vector<ll>& testx, ll mod) {
    if (mod == 0) return 0;
    map<ll, int> cnt;
    for (auto x : testx) {
        cnt[x % mod]++;
    }
    ll ec = 0;
    for (auto& p : cnt) {
        ll f = p.second;
        ec += f * (f - 1) / 2;
    }
    return ec;
}

void print_query(const vector<ll>& nums) {
    cout << 0 << " " << nums.size();
    for (auto num : nums) {
        cout << " " << num;
    }
    cout << endl;
    cout.flush();
}

ll read_c() {
    ll c;
    cin >> c;
    return c;
}

int find_coll_pos(const vector<ll>& seq, int maxk) {
    int lo = 2, hi = maxk;
    int res = -1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        vector<ll> pref(seq.begin(), seq.begin() + mid);
        print_query(pref);
        ll cm = read_c();
        if (cm >= 1) {
            res = mid;
            hi = mid - 1;
        } else {
            lo = mid + 1;
        }
    }
    return res;
}

int find_first_idx(const vector<ll>& seq, int alo, int ahi, int sec_idx) {
    int lo = alo, hi = ahi;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        vector<ll> sub(seq.begin() + lo, seq.begin() + mid + 1);
        sub.push_back(seq[sec_idx]);
        print_query(sub);
        ll cm = read_c();
        if (cm == 1) {
            hi = mid - 1;
        } else {
            lo = mid + 1;
        }
    }
    return lo;
}

int main() {
    const int K = 60000;
    vector<ll> seq(K);
    for (int i = 0; i < K; ++i) {
        seq[i] = (ll)(i + 1) * (i + 1);
    }

    // Initial query
    print_query(vector<ll>(seq.begin(), seq.begin() + K));
    ll total_c = read_c();

    if (total_c == 0) {
        // Second attempt with different sequence
        vector<ll> seq2(K);
        ll offset = 1000000007LL;
        for (int i = 0; i < K; ++i) {
            seq2[i] = (ll)(i + 1) * (i + 1) + offset * (i + 1);
        }
        print_query(seq2);
        total_c = read_c();
        // Assume now total_c > 0, else error but rare
        seq = seq2;
    }

    // Find the position of the first collision
    int l = find_coll_pos(seq, K);  // l is the size where first collision occurs

    // Now find the first_idx in 0 to l-2
    int sec_idx = l - 1;
    int first_idx = find_first_idx(seq, 0, l - 2, sec_idx);

    ll d = abs(seq[first_idx] - seq[sec_idx]);

    // Get divisors
    vector<ll> candidates = get_divisors(d);
    vector<ll> possible_n;
    for (auto dv : candidates) {
        if (dv >= 2 && dv <= 1000000000LL) {
            possible_n.push_back(dv);
        }
    }

    // Prepare test set
    const int TESTK = 30;
    vector<ll> testx(TESTK);
    ll tbase = 1000000000000000000LL / 2;
    ll tstep = 1000000007LL;
    for (int j = 0; j < TESTK; ++j) {
        testx[j] = tbase + (ll)j * tstep;
    }

    // Verify each possible
    for (auto m : possible_n) {
        ll exp_c = compute_expected_c(testx, m);
        print_query(testx);
        ll act_c = read_c();
        if (act_c == exp_c) {
            cout << 1 << " " << m << endl;
            cout.flush();
            return 0;
        }
    }

    // If none, error, but shouldn't happen
    assert(false);
    return 0;
}