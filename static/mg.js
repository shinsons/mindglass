var commandHistory = {
    idx : 0,
    cmd : []
};
var login_form = new Ext.Panel({
    labelWidth: 80,
    bodyStyle: 'background:transparent',
    layout: 'absolute',
    html : '<h1 style="margin-top:10px;margin-left:10px;font-size:3em;"> Mind Glass Login:</h1>',
    id: 'loginForm',
    items : [{
	xtype: 'label',
	text: 'Username:',
	x: 165,
	y: 70,
}, {
	xtype: 'textfield',
	id: 'loginUsername',
	allowBlank: false,
	x: 160,
	y: 88,
}, {
	xtype: 'label',
	text: 'Password:',
	x: 165,
	y: 120,
}, {
	xtype: 'textfield',
	id: 'loginPasswd',
	inputType: 'password',
	allowBlank: false,
	x: 160,
	y: 138,
}, {
	xtype: 'label',
	id: 'msg-label',
	text: '',
    style : "color:red;",
	x: 161,
	y: 167
}, {
	xtype: 'button',
	name: 'login',
    id: 'login-bt',
	text: 'Log In',
	width: 80,
	style: "margin-bottom:10px;",
	x: 230,
	y: 190,
	handler : function() {
        var user_field = Ext.ComponentManager.get('loginUsername');
        var pass_field = Ext.ComponentManager.get('loginPasswd');
        if(!user_field.isValid()){
            user_field.focus();
            return false;
        }
        if(!pass_field.isValid()){
            pass_field.focus();
            return false;
        }
	    this.setIcon('/static/resources/themes/images/default/grid/loading.gif')
	    this.disable();
        Ext.Ajax.request({
            url : 'auth/',
            params : {
               user : user_field.getRawValue(),
               passwd : pass_field.getRawValue()
           },
           success : function(r) {
                var mgvp = Ext.ComponentManager.get('mg-viewport');
                login_window.hide();
                login_window.has_been_shown = true;
				mgvp.add([tree, command, grid]);
                grid.getStore().load();
                tree.getStore().load();
           },
           failure : function(r) {
                var err = Ext.JSON.decode(r.responseText);
                if(err.data && err.data.msg){
                    var err_label = Ext.ComponentManager.get('msg-label');
                    var bt = Ext.ComponentManager.get('login-bt');
                    err_label.setText(err.data.msg);
                };
                bt.setIcon('');
                bt.enable();
           }
        });

	}
}]
});

var login_window = new Ext.Window({
    layout:'fit',
    closable: false,
    draggable: false,
    resizable: false,
    width: 425,
    plain: true,
    border: false,
    bbar: [{
	xtype: 'tbtext',
	text: '&#169;2012. TeraStructure Inc.'
    }],
    items: [ login_form ]
});

login_window.has_been_shown = false;

var treestore = Ext.create('Ext.data.TreeStore', {
    autoLoad : false,
    proxy: {
        type: 'ajax',
        url: 'docs/',
        reader : {
            type: 'json',
            root : 'data'
        }
    },
    root : {
        text : 'MindGlass',
        root : true
    },
    listeners : {
        beforeload : function() {
            tree.mask.show();
        },
        load : function() {
            tree.mask.hide();
            
        }
    }
});

var tree = Ext.create('Ext.tree.Panel', {
    region: 'west',
    title : 'Functions',
    width: 200,
    rootVisible : true,
    scroll : 'vertical',
    store: treestore,
    listeners : {
        afterlayout: function() {
            this.mask = new Ext.LoadMask(this, { msg: "Loading ..." });
        },
        itemdblclick : function(v, r, i, idx) {
            prmpt.setValue(r.raw.cmd);
        }
    }

});

Ext.define('DataFiles', {
    extend : 'Ext.data.Model',
    fields : [
        {name : 'filename', type: 'string'},
        {name : 'path', type: 'string'}
    ]
});

var filestore = Ext.create('Ext.data.Store', {
    model : 'DataFiles',
    proxy: {
        type: 'ajax',
        url: 'files/',
        reader : {
            type: 'json', 
            root: 'data'
        }
    }

});
// create the Grid
var grid = Ext.create('Ext.grid.Panel', {
    title : 'Data Files',
    region: 'east',
    width: 200,
    store: filestore,
    bodyStyle : 'cursor:default;',
    columns: [
        {
            flex : 1,
            sortable : false,
            dataIndex: 'filename'
        }
    ],
    viewConfig: {
        stripeRows: true
    },

    listeners : {
        itemdblclick : function(v,r) {
            prmpt.setValue("scipy.io.loadmat('" + r.get('path') + "')");
        }
    }
});

var prmpt = Ext.create('Ext.form.field.Text', {
    region: 'south',
    padding : '2 2 2 2',
    cls : "cmd-window",
    height: 30,
    listeners : {
        specialkey : {
            fn: function(f, e) {
                if (e.getKey() == e.ENTER) {
                    commandHistory.cmd.splice(0,0,f.getValue());
                    commandHistory.idx = 0;
                    Ext.Ajax.request({
                        url : 'command/',
                        params : {
                            cmd : f.getValue()
                        },
                        success : updateCommand
                    });
                    return false;
                }
                if (e.getKey() == e.UP) {
                    f.setValue(commandHistory.cmd[commandHistory.idx]);
                    
                    commandHistory.idx++;
                    if(commandHistory.idx > commandHistory.cmd.length) {
                        commandHistory.idx = commandHistory.cmd.length;
                    }
                    return false;
                }
                if (e.getKey() == e.DOWN) {
                    f.setValue(commandHistory.cmd[commandHistory.idx]);
                    commandHistory.idx--;
                    if(commandHistory.idx <=0) {
                        commandHistory.idx=0;
                    }
                    return false;
                }
                
            }
        }
    },
});

function updateCommand(r) {
    var command_el = command.items.get(0).getTargetEl();
    var new_el = command_el.insertHtml('beforeEnd',r.responseText, true);
};
var command = Ext.create('Ext.Panel', {
    title : 'Command Window',
    region: 'center',
    layout: 'border',
    style : "font-family:monospace;padding:2px;",
    items : [
        {
            region: 'center',
            autoScroll: true
        }, prmpt],
    listeners: {
        afterrender : function() {
            var command_dom = command.items.get(0).el.dom;
            Ext.EventManager.on(command_dom,'DOMNodeInserted',function() {
                prmpt.setValue('');
                var d = command.items.get(0).body.dom;
                d.scrollTop = d.scrollHeight - d.offsetHeight;
            });
       }
   }
});
