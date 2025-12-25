#include <bits/stdc++.h>
using namespace std;
using ll = long long;

struct Item {
    string name;
    ll q, v, m, l;
};

ll parse_number(const string& s, size_t& pos) {
    ll num = 0;
    while (pos < s.size() && isdigit(static_cast<unsigned char>(s[pos]))) {
        num = num * 10 + (s[pos] - '0');
        ++pos;
    }
    return num;
}

void expect_char(const string& s, size_t& pos, char expected) {
    if (pos < s.size() && s[pos] == expected) {
        ++pos;
    }
}

vector<Item> parse_json(const string& input_str) {
    string json;
    for (char c : input_str) {
        if (!isspace(static_cast<unsigned char>(c))) {
            json += c;
        }
    }
    vector<Item> all_items;
    size_t pos = 0;
    if (pos < json.size() && json[pos] == '{') ++pos;
    while (pos < json.size() && json[pos] != '}') {
        if (pos < json.size() && json[pos] == '"') {
            ++pos;
            size_t key_start = pos;
            while (pos < json.size() && json[pos] != '"') ++pos;
            string key(json.begin() + key_start, json.begin() + pos);
            ++pos; // "
            expect_char(json, pos, ':');
            expect_char(json, pos, '[');
            Item it{key, 0, 0, 0, 0};
            it.q = parse_number(json, pos);
            expect_char(json, pos, ',');
            it.v = parse_number(json, pos);
            expect_char(json, pos, ',');
            it.m = parse_number(json, pos);
            expect_char(json, pos, ',');
            it.l = parse_number(json, pos);
            expect_char(json, pos, ']');
            all_items.push_back(it);
            if (pos < json.size() && json[pos] == ',') ++pos;
        } else {
            ++pos; // skip unexpected
        }
    }
    return all_items;
}

const ll MAX_MASS = 20000000LL;
const ll MAX_VOL = 25000000LL;

void try_greedy(const vector<Item>& items, const vector<int>& order, vector<ll>& best_counts, ll& best_value) {
    vector<ll> this_counts(12, 0);
    ll rem_m = MAX_MASS;
    ll rem_v = MAX_VOL;
    ll val = 0;
    for (int o : order) {
        int i = o;
        ll tm = items[i].m;
        ll tl = items[i].l;
        ll tq = items[i].q;
        if (tm == 0 || tl == 0) continue;
        ll mx = min(tq, min(rem_m / tm, rem_v / tl));
        this_counts[i] = mx;
        val += mx * items[i].v;
        rem_m -= mx * tm;
        rem_v -= mx * tl;
    }
    if (val > best_value) {
        best_value = val;
        best_counts = this_counts;
    }
}

ll best_value;
vector<ll> best_counts;
vector<Item> all_items;
vector<int> branch_order;

void recursion(int bidx, ll cur_mass, ll cur_vol, ll cur_val, vector<ll>& counts) {
    if (bidx == 12) {
        if (cur_val > best_value) {
            best_value = cur_val;
            best_counts = counts;
        }
        return;
    }
    int i = branch_order[bidx];
    ll rem_m = MAX_MASS - cur_mass;
    ll rem_v = MAX_VOL - cur_vol;
    if (rem_m < 0 || rem_v < 0) return;

    // upper bound including current and later
    ll upper = cur_val;
    for (int k = bidx; k < 12; ++k) {
        int j = branch_order[k];
        ll tm = all_items[j].m;
        ll tl = all_items[j].l;
        ll tq = all_items[j].q;
        if (tm == 0 || tl == 0) continue;
        ll mx = min(tq, min(rem_m / tm, rem_v / tl));
        upper += mx * all_items[j].v;
    }
    if (upper <= best_value) return;

    ll this_m = all_items[i].m;
    ll this_l = all_items[i].l;
    ll this_v = all_items[i].v;
    ll this_q = all_items[i].q;
    ll maxx = 0;
    if (this_m > 0 && this_l > 0) {
        maxx = min(this_q, min(rem_m / this_m, rem_v / this_l));
    }
    for (ll x = maxx; x >= 0; --x) {
        ll new_mass = cur_mass + x * this_m;
        ll new_vol = cur_vol + x * this_l;
        if (new_mass > MAX_MASS || new_vol > MAX_VOL) continue;

        // tighter upper for this x
        ll upper_rem = 0;
        ll nr_m = MAX_MASS - new_mass;
        ll nr_v = MAX_VOL - new_vol;
        for (int k = bidx + 1; k < 12; ++k) {
            int j = branch_order[k];
            ll tm = all_items[j].m;
            ll tl = all_items[j].l;
            ll tq = all_items[j].q;
            if (tm == 0 || tl == 0) continue;
            ll mx = min(tq, min(nr_m / tm, nr_v / tl));
            upper_rem += mx * all_items[j].v;
        }
        if (cur_val + x * this_v + upper_rem > best_value) {
            counts[i] = x;
            recursion(bidx + 1, new_mass, new_vol, cur_val + x * this_v, counts);
        }
    }
    counts[i] = 0;
}

int main() {
    string input_str((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    all_items = parse_json(input_str);
    if (all_items.size() != 12) {
        // error, but assume correct
        return 1;
    }

    vector<ll> counts(12, 0);
    best_value = 0;
    best_counts = counts;

    vector<int> order(12);
    // first greedy v/m
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [](int a, int b) {
        return (__int128)all_items[a].v * all_items[b].m > (__int128)all_items[b].v * all_items[a].m;
    });
    branch_order = order; // use this for branching
    try_greedy(all_items, order, best_counts, best_value);

    // second greedy v/l
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [](int a, int b) {
        return (__int128)all_items[a].v * all_items[b].l > (__int128)all_items[b].v * all_items[a].l;
    });
    try_greedy(all_items, order, best_counts, best_value);

    // third greedy v/(m+l)
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [](int a, int b) {
        ll am = all_items[a].m + all_items[a].l;
        ll bm = all_items[b].m + all_items[b].l;
        return (__int128)all_items[a].v * bm > (__int128)all_items[b].v * am;
    });
    try_greedy(all_items, order, best_counts, best_value);

    // now search
    recursion(0, 0LL, 0LL, 0LL, counts);

    // output
    cout << "{" << endl;
    for (int i = 0; i < 12; ++i) {
        if (i > 0) cout << "," << endl;
        cout << " \"" << all_items[i].name << "\": " << best_counts[i];
    }
    cout << endl << "}" << endl;

    return 0;
}