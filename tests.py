# import requests
# import pprint

# tokens = [

# 'simplylolo:Diepold1.0:tndx36suf04ukf6v5qvoq1eboatjlk',
# 'jmanatee33:654321aca:q30sg3v93mequ8jjdbswe4bo8hkyct',
# 'munizola:1vda3n6hf:na095aesns4x4advj6hc82yiublc2b',
# 'earthbound10:bobo36488:zzn7eqz6lyvhf4htemzqewn0ug1hya',
# 'darsenftw:lolxdxp123:e5rrbtmynuwgs0l63311kvunyb0rqw',
# 'swagboth:20011220:spa7purlti4hzaewl0934t6dl4dqll',
# 'maitreasakey:16112000:1EjW36vrHYqku4DfEzedoehcLdB9evYEas',
# 'x67633855:xx758520:4iyk9la6aa1peuviu0348868x3sw57',
# 'scv1849:cks1232456:6wf7g2x8kaviybbpl6mgfz6pzj8ilo',
# 'yasser6525:As0554933856:5nqciz8p0xygrjstxgpztmld6yb2os',
# 'gimmeyagotdamnvegatables:Espana10:o249t3s1fb9cu3p3tnbwn059alt3qs',
# 'pubgismyfavoritegame:16892405:6xjf2kx34c1z94w7idkkibul2m7eyi',
# 'lujksz:166198716l:bostxg0catxmpyjqjrm5enqk1t85ys',
# 'vandsonsantoss:34219595:1EjW36vrHYqku4DfEzedoehcLdB9evYEas',
# 'mrc_krk:Erchaakal1:753vcr51ihricepgye8mhnee3l8njz',
# 'minecrafter4lyfe549:47y8nfpq:yh07esmkdg1xgdunaktqsw62y14l9g',
# 'kennybell:chester123:crrolofwf3bty1mc6a7jb1l4rqg5g0',
# 'superpabloski:1234wxyz:hcrpklnbjj9jrcuumlkxgwbol2rksz',
# 'pin_head_larry4:Zockon123:umorrux2n4zfif54vp7t0tqkor1myz',
# 'birdalberkan:fenerbahce1:iq451rp57cugejakl3b5k1b7kwe8sp',
# 'dwarfter:49375092:rmp6i5vkmskag4z67u0qchh4y3wt5g',
# 'dawid70970:kaja2235:rzuvya3bfv777pcyapt7989aw3cbbp',
# 'yongoh11:ghkdxjf1:tco80ng72ciwlzv2qea004rjmzkto9',
# 'dlwlgh0123:asd258258:qhgvryvteneey9p6xz0b0tft3upfmw',
# 'wolfcorexpert_:Chelsi11:2y1wak121kxmge8mfhluxgm8o8pgco',
# 'aztroos:49684215:qyjhs03y1li9w3s0red5bw64pomt05',
# 'azer95bharini:21499604:upbqlwosnd2qeove8mhcowutt3ikpe',
# 'venitas751:Asaspades3:x04e939vwffkm2t2o6wld4g6r032ja',
# 'beefy_nsa_tech_nerd:Jajajim3:h577v05x4vgcihzc32kzpbizpfkv52',
# 'omegahertz:09091998:u8ncopc2lrzva9yq9e8fs61c99yvxf',
# 'soban_plz:grawer0911:rrm2r8v1p4x8d4rekfxvhnjephq4yk',
# 'deaxh420:Jack2all:edto1jk31iz6ju3akt5otr219crmkz',
# 'supipara:1234qwer:g4nybgoyhrgwufsz7bcsyssmpnsoch',
# 'blockbuilder2:robin1997:1EjW36vrHYqku4DfEzedoehcLdB9evYEas',
# 'rampage304:Goobas123:5m5jl7pwqporhlamdnk33twcst2mti',
# 'underpantsoverpants:Aiptek1!:a6f3g4kyajish33hsum9ire7a2y3vp',
# 'tirasillashd:sumorenito19:xg7oxdg0b8qvhdudwwg5wrsv52hqby',
# 'koksotron_:258456aa9:a8mowrmp6pvq6y9vmupmtigubpxb0v',
# 'samsoussana:ronnie77:nll47ggs5ujv8x9etl3ar6q9zou6fw',
# 'jeffry535:yfri535535:chl6krq70bcqv0mpv9g5ds8my6vb4r',
# 'stalinsnan:saturn15:mxhdrwais8l7jecre0x79n2bi2yrn8',
# 'flhf:0532AArr:jf9dkcd7sxurnd8aprvtjt3a4uy9wt',
# 'planningmyescape:Skippy1086:0qr9pd0mz3d1xu9mw4ft8a1n4e1med',
# 'lukogreen:morpheus:06ks6rsk38fniu0d1nobd4615sqnal',
# 'pdpm19:pedro919420240:v68qpn1q44j4da796ok2rpiirimqsx',
# 'bence4444:9bfd6112b4:i3a8iefgjagly88nteign6chi2h7yb',
# 'lurkingdefiler:1forgotit!:qkh6mcdkdhqbehu0bh9oe14yl3kqln',
# 'miamidolphins1122:Jersey19:hfq3e5wywne1foghj7jartnd44hqu1',
# 'nesegruser:123martin:ai1bwgpsibkh51o9iutb0ee7n0jwtp',
# 'prokaza44:Stalker123:yyi7u4vp300xbo89hmclm4r6sc1qi5',
# 'barvyy:15975342680:yav4u40co118mbq88qbh6uhark0ri6',
# 'timurace:3027Tim1401:1EjW36vrHYqku4DfEzedoehcLdB9evYEas',
# '3dwardy33:edward9570:rguhw78o9zyugvk1cs1m0b9hdyiwqw',
# 'galaxy_fbr:minecraft:qzqx0nsa5k4gzbxzouf2plhwoaqcfm',
# 'tndhks0525:k1019014:8bcizz3u2vbvmvf337xnjn8h3b1oqj',
# 'sulivaneze:Jeremylecon1:jpnqo2qcft2fk3c1yyh1ybbt3z1er5',
# 'tifa54:Juliea54550:t00l0g9y1s9b0oml7oupf9lo5y5tjz',
# 'tysonhitemup:Tyson1644:2l44xoesp8vl05x0a2c6ayfyax61i4',
# 'bergwr:132fbee4:v741c93fygambz0hcy8fd2ot1hyvqx',
# 'loadhook6167:Henry1105:x0cibea5lqab9gucsp2tjcsob5lxyq',
# 'noxx_1337:philipp2011:zoijb6pahncco12gsxymr0ox78z30w',
# 'xraiderx993:horizon@:bkc8dzj89y89q0s9n4ur26otoy22l5',
# 'trayb123:Kitebuggy55:8e4xs8l8ifv9lizl0ct25ol62pnqad',
# 'alacna:deoxys-12:kd0qcdtz2cjvqe40lig7f7ppnsitza',
# 'skillfulshot42:Shubada12:69k6ecesactguatw2zffkb4z2aa677',
# 'baskosmusic:Clichy92:msa4n4gspt43jkelvhjlntlc8it6y0',
# 'cjshd101:Football17:zsik6dotcsjk248qhzgn0slgh8euut',
# 'specko993:04121993:89fg1d8trq1z622i2jc1lkuzi6qmvy',
# 'likalli:Magazin1:hn9nmpkdedvlsxrg7kf6oihwyndwdl',
# 'depressedspud:78andrew:c2mu3they259qny5d731cy8sbux3ky',
# 'pawlidick:sawforever23:botrm0z6rka5e2uebe3bo4uw753qz9',
# 'gamelegend429:battlecry4:yitqakv4ja3pnhhr78jfzituusvrh7',
# 'bravokillyou:trucoteca:ljwahh05fxivm4zq5exp1kcoojplq2',
# '4n0nym1911:wasilij4423:8vivj5t27ho6c7a0ngu4ol2aed8vgy',
# 'iceboundwriter9:BeAn84848484:94dtcjrk2s2cv32ivju9z7x0tbdd48',
# 'ali_rosario:10101m1a:465ntllgjnsx9g47n7rj843y2isxcg',
# 'broneboyrus:g7g72s6w:kp1ph2dpczdrk1th08lr7bhi7n7x9p',
# 'mankinimist:Cloppety1:9iope9e7t0290csjhyhxvrw5f0hw4c',
# 'smohrs:soccer09:0p2km276h3rrvu9f46y4gnuvmr7ndt',
# 'mokisworld:Jroc1323:q9711jafru7pv6chadwb7w2v0eep5g',
# 'chadalli:Ulysse94:r9kf4a22p5oylcl91hzx0yjf85bjw7',
# 'kfulks:kaleigh1:5ase4arqly86kwj0vs358xrei9hiw1',
# 'lol512:111836qa:vxxag3dzt0o2qcav03pz1e2ozatbpj',
# 'ruanthow:34627034:r9c7j2nbzu5a9b5smun5lty8i5d76s',
# 'mzbish:Pimpin121:hwvcj1r61ypxrpqq56x9mur6jiv0i1',
# 'nice95c:1207nice:ueggxmk9lvddrlx1gk9pmrbypvbghj',
# 'matsu334:Matsumoto33:kybrwu3dpnc87dymt0dtji8hcguz4p',
# 'allanwinn:play1234:2jnamfj8lv0s4wf70nps91y902i4iq',
# 'rama2004:skype123:0qwy88oet29h10khc1sa6usixzqxe2',
# 'r_seib:8148992983:79zueht19tgjkwvjhbrgc6aa8pdhuc',
# 'excelentt:filelist1:s4lme433fhzm9ayidz9ano8qhlhqki',
# 'hellojudas:something123:fwspwx02smfjqqoxnti69bpbat0qqx',
# 'wasserkefir:Caruso1608:nqewpkpk3dacetaugqr5mfg0ewf8d7',
# 'yurasjak:hahadobrexd:9io3cjhsg1qts6pbebh3m9tawx7ize',
# 'beeftwinkie_tv:indabay510:0kmkz5a02pf6oc0dtg7ilbz3z2cx9o',
# 'felipedream1:Issues422:5cw8aa9irdk4qfz0c4ga81zgemswa5',
# 'wjdgustj12:wjdgustj0613:sck14gxzeola9zo1sj570mqgvkplj1',
# 'sootharath:Jordan8497:6pbdx15chhkkm2l4ke21r3l9z0qfn3',
# 'jese37:Jonathan07:uxq6n4mkjk0z4uf23zfwnq5eiiv7wu',
# 'sixkr:22112002:rrqi2z12wae12oj1nw678qv63b3gca',
# 'adam99887:32349704:c2iwrcckxoulwyboypv7srxg0waujz',
# 'fktd123:1234567890q:u9dagzsz1mruh8hdmmw6swb5tom2aq',
# 'jabbleston:mountainhawk:e991y23ag05goagr3zk216ciiqw86m',
# 'buckx3:thefrog505:tkv7e4k9jyqfcgp9ztnppkot5ldhqx',
# 'plazmacs258:258456ks:at7dvqwjoxrlxpnug0vepjq7478sf9',
# 'sao5482:laguna1682:i5xkpmaiilq4rg02r3yfwadc68v4iq',
# 'ryanryry3:hulk2000:zdsvwt7hbxvyzao6t5i2gneomrdlct',
# 'basoyang:787898ace:ryei8gppn0pb6gwlz2hlwmkpm0i5gx',
# 'xhelanqa:xhelanqa123:2y7fgxx1tn4hybp0y4hgoqfkjdfd7g',
# 'janfelix07:janfelix07:1EjW36vrHYqku4DfEzedoehcLdB9evYEas',
# 'ahn_gi_hyo:951852zz:znz270ooqh1tywsrydr75l6jufbw07',
# 'ismaeltoscano15:191119111911itp:g3ixkr456a5ze8robagxj8scelzgxh',
# 'nachobbt:20122012n:xddppoa7j68ekm2rmeqrerw8akf70l',
# 'pipesucio:231097mhrr:y2zjt2nyh6zkunp0b61zjjbse5yfyr',
# 'pro_slack:gz3392ug:j4ebcinzoavf5g05uuf5fdfh0owptz',
# 'blauver0803:Bl129616:plsxsmfm2kxneqvo4wsqwf9b0m3hfl',
# 'trabdutrab:81551381:r48uhnwv17ahlbyqse8we3os31rnj9',
# 'xkingabart:191297mss:z62g8hxjjuttibj82ylfssclzvt1hd',
# 'tailrnb:tail5127:09gavw9wj7r0ic8fvfoq7hbb4qxb05',
# 'blackdragneel:96284283:flsxtsghggizttsm4x7w251bm5155q',
# 'zevers23:huskers#1:f53z52kpgc3rlj58rd6ew1uqcu1iat',
# 'jdiaz0:30052410:lbzd59xwil366k4nzs989jxauwvogi',
# 'kyuji92:931499bear:qga40gr7twxe1828r9o27akaua1vet',
# 'theterriblestream3:baseball11:7fbty8t0nd1rshj4y3snq01hnsye4v',
# 'derilem:Scorpion06:pt8e5jfki8htthmn4ksttvcnktyvzc',
# 'pokemondemais:sac132909:kq0fo8h2ipt1g19tydcafvzyndcawa',
# 'capitaina77:Bouchard77:m6uledp8n6cznufkn1ampqovcz2fhz',
# 'fine_thrust:tony8797:q73f1ff2v6gxxpv0dx26ja9t4pmt8k',
# 'saylasnz:lheg201124:hc43lyv948pie1db4z2i6ux9375pk2',
# 'cptwreckaho:311magdaleno:8pqql74vkr4mo0djnwl3fr4vye578b',
# 'sweetp18:priscila01:4bq6oun4e6vlrg91nd8xrwxuh3qje2',
# 'zryan39:perkybutt2233:p8b197kz7xy75gwkxoqtj0ggkza6vn',
# 'helianthus13:Clintm13!:a69wxy54zarvxsqllwgprwl4y52m36',
# 'hearthstoneed:delgado4:4c7xn5mazdp2ahf3wts6nx4wn27l0t',
# 'kejn98:chistoria123:m15fe5xndmaa4r2t3lhb4f3zue0uje',
# 'papitermidor69:22032203gaby:60nk9go8j7u9f9d14sof0657yial22',
# 'dobeca12:ataforever1:hcg9h5r1yp67os0wrutnfvjgqnz857',
# 'danielaboccia01:simon3000:ib46mxo444tw215vy6u1agrqls4vdo',
# 'pichon1997:bioshock2:jbwt6bue5g1epsp5rnqycpvpso5tug',
# 'duske77:birger2806:rs0p52hp773tzto7mz5rnvhieht31w',
# 'ladyyk:plasma12:1EjW36vrHYqku4DfEzedoehcLdB9evYEas',
# 'brankooo9:basienka123:tl96vdbkbejy2wyut9fo6yfworssry',
# 'reflosh:qwaszx123:ge99pb4nkf65s21fkro3mta1ddodm3',
# 'anosa1:Soccerpro33:us0fr8s3tpswq9rm5j3i58ccx4nmrl',
# 'rauliutub:asdqwe123:e2jd7dnyi6qscxl4nhr2dn0ismoqhs',
# 'rafaliba_:Minhasenh4:hcxa6huu7gcmljp0hcttq1avhag9t9',
# 'benitogan_:Ordenador97:jpyvgvdg9rqsyw4jo08jr86nmmhscl',
# 'sing216:qwehk21642:i520egu5m37w4gagf2drxfkp7jadfe',
# 'vaafiie:Mallorca1:f5jsparte522k2fkp90bcs1m1ltmaz',
# 'dydekrl:gmrtjr1ehd:fxonubf3qycwnnlsl9c683g4isujjo',
# 'yahiko_cccp:Retro213:in2odgmdgyngnvqqgjmtt2c8885b5s',
# 'rapidfries:24071998:eec59hhtlq03v30k8kd1olhdwdj63t',
# 'szamanello8:matii0888:k8xs71y91p7gvmdxivsuy2jqec709d',
# 'hamizakart:123+-963:rr69lh252cjwjwvxhmmvy6fhvsp9mg',
# 'uptownkiller:Tnusnus1:0e5xmsykkw6il8imuge6vdxyo17xsy',
# 'cyprustream1:omonoiaka123:726q0g63h5e8pjwr5cnui2te48jd4q',
# 'max4142:1Max1209:ilwsds7v7dsc740bmcz9dr2e9izrfp',
# 'wolf9325:tlsqld12:2cunyoiihp0uz6lmug6zdev8f9g8hv',
# 'kenajster:Kenaj240674:wkp918591thcgpfikvu6ctwqq8sdp9',
# 'luitgard56:rubens56:89t4q94jjx7wm9o1l3q85h1ubkbqae',
# 'douglasmarcolino:flamengo4:ddc64mfol1kcvj76zo3s3g1vo01hx4',
# 'lordogar1:Qwerty2206:z6lxx58m6a8yyqibu27ux96nj1ovfb',
# 'samitoalves52:colombia8:g69zrmemgbalrkfsgtpcivj0fpwyrb',
# 'theshattered22:jasper222:s0nmevp9bxwhlhlih5ezl1l7djh2x7',
# 'pac3k:wacek123:dt2g2axzyp8hwtbv9skmfi7r5ct8x6',
# 'sdk1234567:sdk1995728:sqmjanirvb8ltsy4dboclfxncc1dg5',
# 'hotm_jay:Coffey0827:b99ef1lwanest5dr290uw0bwi1jmak',
# 'bforosisky:Michael1993:5zl1u74fvnelasvbc7fhw9ssp2xb8w',
# 'furaika:dlqudwn1:u6sbu7vd9z6dh6uy0bdubdlikcp1ko',
# 'liverkim12:liverpoolfc5:twp2qvo3kfsmmy3w0oj5cfmbdhfatg',
# 'joethedrunk:188974321:1EjW36vrHYqku4DfEzedoehcLdB9evYEas',
# 'shizuodoge:13011301:ajyo5apmrs6koqbsa3cjff05u7jugb',
# 'dedolla:bone0078:j2vec2l5033b40x4qcpjgwbibhytr6',
# 'yellowmonkey1987:2011Jasper:z570825vw78ekbdrcew6xwdxbo5kra',
# 'sd_blaze:Champion01:mshwj0lkzo8i5fjmou8f30yzrl4m9g',
# 'wolfking777:grandknight:ek0fado0w4qq5rprchjvjrwaxd4vty',
# 'purevillain86:Asas1234:cw3gbsholysw925et8zeit9r8myy7c',
# 'lucho11402:mochima224:bzvaeqxary1qthnbfp65t1ree26353',
# 'beshrew11dmeyg:otz310110:8xtcrbfmp7x901f7ljtjmky94la5fo',
# 'genius1095:95cjswo!:c4w3h85emjvrw6jwxm8964mouddzen',
# 'cosmicspin9:Airstrike88:lp1qf2g6myp9vkqqzdyqwn3paxwhc6',
# 'dalt0n4mvp:devils09:wqg3rtm0inyreev9e67adnknylxrki',
# 'pedrompires01:Benfica17:mt5327umxhnerprzcu1hxecam6bq7s',
# 'fridatamm:Cachubis:1EjW36vrHYqku4DfEzedoehcLdB9evYEas',
# 'sketch232:Ar1se232191:yh89xwilq1m3ib8xd2rhr0kxt3a3ql',
# 'gogogory:evangelina117:74cufg7ofkmogshe0uyodkmdlhe7w7',
# 'eggsmckinley:8394545s:c4um6932swhwpqx82m4fekja342z6b',
# '18205209966:q18205209966:sy947kbss1vknm08n5qrg9m9qu8of9',
# 'l2tucu:1elvis23:ou98ynpsj9yqr2pgli8azv2ummxxdp',
# 'ckacl1115:alscks937:xrrmkm16ajwk8o8v9ynxpz9r6xyehz',
# 'gametag1996:Ratrace24:x5r2xb26hxr873mbuhz4w6krvig437',
# 'squipo:Wertyo87:w656ne25slxifgh3k1z15f0ntglucl',
# 'tezzetngo:fILIPE007:e9j13xudo63kmnfl6blpjwtf97nax9',
# 'nickhina:Hinatahyuga1:oxkpy7ufxno0ultxq5mnf3a8o754b5',
# 'oldskoolnewb:blaze420:r3evd22bmohn198u6tmtdeeen42j2u',
# 'necrofil2010:314pltyrF:0cxa8b8mu860hg5t1zfoxtztl7w4yo',
# '6yym6yym:Q1wertyui:e3822p9jet09j1lawkq99actj1ij91',
# 'artvlg:burger12:qeo1nltuy3iahnv0gnajxk1mhmw6s9',
# 'duncancandoit:redhead1:jmmfw41ahbairqx4lurt6dwpo4c9g3',
# 'houtarou96:pokemon96:i0umhncg83dqx03ckercu5o3tx6xfb'


# ]

# print(len(tokens))
# for i, code in enumerate(tokens):
# 	headers = {"Authorization": f"OAuth {code.split(':')[-1]}"}
# 	r = requests.get("https://id.twitch.tv/oauth2/validate", headers=headers)

# 	if r.status_code == 200:
# 		print(code)
# 	else:
# 		print('no', i, code.split(':')[-1])
# 	# print(r.status_code, r)
# 	# print(r.content)
# 	# pprint.pprint(r.json())


import pytz
from pytz import timezone
from datetime import datetime



# print(pytz.all_timezones)

# # time = '20:33'
# time = datetime.strptime('20:00 Japan', '%H:%M %Z')
# print(time)
# # print(type(date_time_obj))
# # print(date_time_obj)

# # timezone = 'Etc/GMT-1'
# # tzone = timezone('Etc/GMT-1')
# tzone = timezone('Etc/GMT-1')
# date_and_time = time.astimezone(tzone)
# # print(date_and_time)
# date_and_time_in_text = date_and_time.strftime('%H:%M')
# print(f"CET - {date_and_time_in_text}")



# get the standard UTC time  
# UTC = pytz.utc 
  
# it will get the time zone  
# of the specified location 
# IST = pytz.timezone('Asia/Kolkata') 
  
# # print the date and time in 
# # standard format 
# print("UTC in Default Format : ",  
#       datetime.now(UTC)) 
  
# print("IST in Default Format : ",  
#       datetime.now(IST)) 
  
# # print the date and time in  
# # specified format 
# datetime_utc = datetime.now(UTC) 
# print("Date & Time in UTC : ", 
#       datetime_utc.strftime('%Y:%m:%d %H:%M:%S %Z %z')) 
  
# datetime_ist = datetime.now(IST) 
# print("Date & Time in IST : ",  
#       datetime_ist.strftime('%Y:%m:%d %H:%M:%S %Z %z')) 


# ==========
# IST = pytz.timezone('Asia/Kolkata') 
# UTC = pytz.timezone('Etc/GMT-1') 
# # print(IST)
# print(datetime.now().strftime('%H:%M'))
# print(datetime.now(IST).strftime('%H:%M'))
# print(datetime.now(UTC).strftime('%H:%M'))
# print(datetime.now(UTC).astimezone(timezone('Asia/Kolkata')).strftime('%H:%M'))
# ==========


# time = datetime.strptime("13:00 Asia/Kolkata", "%H:%M %X")

# time = datetime(1970, 7, 10, 18, 44, tzinfo=tz)
# print(time)

# Given time and timezone
# given_time = '21:00 pm'
# # given_timezone = 'Asia/Kolkata'
# given_timezone = 'Brazil/West'

# # Format given time
# given_date = datetime.strptime(given_time, '%H:%M %p')
# print(f"Given date: {given_date.strftime('%H:%M %p')}")

# # Convert given date to given timezone
# tz = pytz.timezone(given_timezone)
# time = datetime.now(tz=tz)
# time = time.replace(hour=given_date.hour, minute=given_date.minute)
# print(f"Given date formated to given timezone: {time.strftime('%H:%M %p')}")
# print(time.hour)

# # Converting date to UTC

# UTC = timezone('Etc/GMT-1')
# date_to_utc = time.astimezone(UTC).strftime('%H:%M %p')
# print(date_to_utc)



# sp = datetime.now(timezone('Brazil/East'))
# print(sp.strftime('%H:%M'))

# d = pytz.timezone('Etc/GMT').localize(sp.strftime('%M'))

# print(d)


# timestring = datetime.now(timezone('Brazil/East')).strftime('%H:%M')

# # Create datetime object
# given_time = datetime.strptime(timestring, "%H:%M")
# # Set the time zone to 'Europe/Paris'
# converted_time = pytz.timezone('Etc/GMT').localize(given_time)
# print(given_time.strftime('%H:%M'), given_time.tzinfo)

# # Transform the time to UTC
# converted_time = converted_time.astimezone(pytz.utc)
# print(converted_time.strftime("%H:%M"), converted_time.tzinfo)