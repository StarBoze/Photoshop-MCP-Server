"""
レタッチコマンド実行モジュール

このモジュールは、生成されたレタッチコマンドをPhotoshopに送信して実行します。
"""

import logging
import json
from typing import Dict, Any, List, Optional
import asyncio

from photoshop_mcp_server.bridge import get_bridge, PhotoshopBridge

# ロガーの設定
logger = logging.getLogger(__name__)

class RetouchCommandExecutor:
    """レタッチコマンド実行クラス"""
    
    def __init__(self, bridge_mode: str = "applescript"):
        """
        初期化
        
        Args:
            bridge_mode: 使用するブリッジモード
        """
        self.bridge_mode = bridge_mode
        self.bridge = get_bridge(bridge_mode)
        logger.info(f"RetouchCommandExecutorを初期化しました (bridge_mode: {bridge_mode})")
    
    async def execute(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        レタッチコマンドを実行する
        
        Args:
            commands: レタッチコマンドのリスト
            
        Returns:
            実行結果のリスト
        """
        results = []
        
        if not commands:
            logger.warning("実行するコマンドがありません")
            return results
        
        logger.info(f"レタッチコマンド実行開始: {len(commands)} コマンド")
        
        for i, command in enumerate(commands):
            try:
                cmd_type = command.get("type", "unknown")
                cmd_params = command.get("params", {})
                
                logger.info(f"コマンド実行 [{i+1}/{len(commands)}]: {cmd_type}")
                
                # コマンドタイプに応じた処理
                result = await self._execute_command(cmd_type, cmd_params)
                
                # 結果を記録
                execution_result = {
                    "command": command,
                    "status": "success",
                    "result": result
                }
                results.append(execution_result)
                
                logger.info(f"コマンド実行成功: {cmd_type}")
                
            except Exception as e:
                logger.error(f"コマンド実行エラー: {e}")
                # エラー情報を記録
                execution_result = {
                    "command": command,
                    "status": "error",
                    "error": str(e)
                }
                results.append(execution_result)
        
        logger.info(f"レタッチコマンド実行完了: {len(results)} 結果")
        return results
    
    async def _execute_command(self, cmd_type: str, cmd_params: Dict[str, Any]) -> Any:
        """
        コマンドタイプに応じた処理を実行する
        
        Args:
            cmd_type: コマンドタイプ
            cmd_params: コマンドパラメータ
            
        Returns:
            実行結果
        """
        # 基本的なコマンドタイプの処理
        if cmd_type == "adjustBrightness":
            return await self._adjust_brightness(cmd_params)
        elif cmd_type == "adjustContrast":
            return await self._adjust_contrast(cmd_params)
        elif cmd_type == "adjustSaturation":
            return await self._adjust_saturation(cmd_params)
        elif cmd_type == "adjustExposure":
            return await self._adjust_exposure(cmd_params)
        elif cmd_type == "adjustCurves":
            return await self._adjust_curves(cmd_params)
        elif cmd_type == "adjustLevels":
            return await self._adjust_levels(cmd_params)
        elif cmd_type == "adjustHueSaturation":
            return await self._adjust_hue_saturation(cmd_params)
        elif cmd_type == "adjustColorBalance":
            return await self._adjust_color_balance(cmd_params)
        elif cmd_type == "adjustVibrance":
            return await self._adjust_vibrance(cmd_params)
        elif cmd_type == "adjustWhiteBalance":
            return await self._adjust_white_balance(cmd_params)
        elif cmd_type == "adjustShadowsHighlights":
            return await self._adjust_shadows_highlights(cmd_params)
        elif cmd_type == "applyFilter":
            return await self._apply_filter(cmd_params)
        elif cmd_type == "createAdjustmentLayer":
            return await self._create_adjustment_layer(cmd_params)
        elif cmd_type == "runAction":
            return await self._run_action(cmd_params)
        elif cmd_type == "executeScript":
            return await self._execute_script(cmd_params)
        else:
            # 未知のコマンドタイプの場合はJavaScriptとして実行
            return await self._execute_custom_command(cmd_type, cmd_params)
    
    async def _adjust_brightness(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """明るさを調整する"""
        value = params.get("value", 0)
        script = f"""
        // 明るさ調整
        var brightnessCmdDesc = new ActionDescriptor();
        brightnessCmdDesc.putInteger(charIDToTypeID('Brgh'), {value});
        executeAction(charIDToTypeID('BrgC'), brightnessCmdDesc, DialogModes.NO);
        "明るさを{value}に調整しました";
        """
        result = await self.bridge.execute_script(script)
        return {"value": value, "result": result}
    
    async def _adjust_contrast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """コントラストを調整する"""
        value = params.get("value", 0)
        script = f"""
        // コントラスト調整
        var contrastCmdDesc = new ActionDescriptor();
        contrastCmdDesc.putInteger(charIDToTypeID('Cntr'), {value});
        executeAction(charIDToTypeID('BrgC'), contrastCmdDesc, DialogModes.NO);
        "コントラストを{value}に調整しました";
        """
        result = await self.bridge.execute_script(script)
        return {"value": value, "result": result}
    
    async def _adjust_saturation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """彩度を調整する"""
        value = params.get("value", 0)
        script = f"""
        // 彩度調整
        var hslDesc = new ActionDescriptor();
        var hslAdjDesc = new ActionDescriptor();
        hslAdjDesc.putInteger(charIDToTypeID('Strt'), 0);
        hslAdjDesc.putInteger(charIDToTypeID('Satt'), {value});
        hslAdjDesc.putInteger(charIDToTypeID('Lght'), 0);
        hslDesc.putObject(charIDToTypeID('Adjs'), charIDToTypeID('HStr'), hslAdjDesc);
        executeAction(charIDToTypeID('HStr'), hslDesc, DialogModes.NO);
        "彩度を{value}に調整しました";
        """
        result = await self.bridge.execute_script(script)
        return {"value": value, "result": result}
    
    async def _adjust_exposure(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """露出を調整する"""
        value = params.get("value", 0)
        script = f"""
        // 露出調整
        var exposureDesc = new ActionDescriptor();
        var exposureAdjDesc = new ActionDescriptor();
        exposureAdjDesc.putDouble(stringIDToTypeID('exposure'), {value});
        exposureAdjDesc.putDouble(stringIDToTypeID('offset'), 0);
        exposureAdjDesc.putDouble(stringIDToTypeID('gammaCorrection'), 1.0);
        exposureDesc.putObject(charIDToTypeID('With'), stringIDToTypeID('exposure'), exposureAdjDesc);
        executeAction(stringIDToTypeID('exposure'), exposureDesc, DialogModes.NO);
        "露出を{value}に調整しました";
        """
        result = await self.bridge.execute_script(script)
        return {"value": value, "result": result}
    
    async def _adjust_curves(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """トーンカーブを調整する"""
        # パラメータからカーブポイントを取得
        points = params.get("points", [])
        channel = params.get("channel", "RGB")
        
        # JavaScriptコードを生成
        points_code = ""
        for point in points:
            input_val = point.get("input", 128)
            output_val = point.get("output", 128)
            points_code += f"curvePoints.putPoint(charIDToTypeID('Pnt '), {input_val}, {output_val});\n"
        
        script = f"""
        // トーンカーブ調整
        var curvesDesc = new ActionDescriptor();
        var curveDesc = new ActionDescriptor();
        var curvePoints = new ActionList();
        
        // チャンネル設定
        curveDesc.putString(charIDToTypeID('Chnl'), '{channel}');
        
        // カーブポイント設定
        {points_code}
        
        curveDesc.putList(charIDToTypeID('Crv '), curvePoints);
        curvesDesc.putObject(charIDToTypeID('With'), charIDToTypeID('Crvs'), curveDesc);
        executeAction(charIDToTypeID('Crvs'), curvesDesc, DialogModes.NO);
        "トーンカーブを調整しました";
        """
        result = await self.bridge.execute_script(script)
        return {"channel": channel, "points": points, "result": result}
    
    async def _adjust_levels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """レベル補正を行う"""
        shadow = params.get("shadow", 0)
        midtone = params.get("midtone", 1.0)
        highlight = params.get("highlight", 255)
        
        script = f"""
        // レベル補正
        var levelsDesc = new ActionDescriptor();
        var levelsAdjDesc = new ActionDescriptor();
        var levelsAdjList = new ActionList();
        
        // RGB調整値
        var levelsAdjItem = new ActionDescriptor();
        levelsAdjItem.putInteger(charIDToTypeID('Blck'), {shadow});
        levelsAdjItem.putDouble(charIDToTypeID('Gmm '), {midtone});
        levelsAdjItem.putInteger(charIDToTypeID('Wht '), {highlight});
        levelsAdjList.putObject(charIDToTypeID('Lvl '), levelsAdjItem);
        
        levelsAdjDesc.putList(charIDToTypeID('Lvls'), levelsAdjList);
        levelsDesc.putObject(charIDToTypeID('With'), charIDToTypeID('Lvls'), levelsAdjDesc);
        executeAction(charIDToTypeID('Lvls'), levelsDesc, DialogModes.NO);
        "レベル補正を適用しました";
        """
        result = await self.bridge.execute_script(script)
        return {"shadow": shadow, "midtone": midtone, "highlight": highlight, "result": result}
    
    async def _adjust_hue_saturation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """色相・彩度を調整する"""
        hue = params.get("hue", 0)
        saturation = params.get("saturation", 0)
        lightness = params.get("lightness", 0)
        
        script = f"""
        // 色相・彩度調整
        var hslDesc = new ActionDescriptor();
        var hslAdjDesc = new ActionDescriptor();
        hslAdjDesc.putInteger(charIDToTypeID('H   '), {hue});
        hslAdjDesc.putInteger(charIDToTypeID('Strt'), {saturation});
        hslAdjDesc.putInteger(charIDToTypeID('Lght'), {lightness});
        hslDesc.putObject(charIDToTypeID('With'), charIDToTypeID('HStr'), hslAdjDesc);
        executeAction(charIDToTypeID('HStr'), hslDesc, DialogModes.NO);
        "色相・彩度を調整しました";
        """
        result = await self.bridge.execute_script(script)
        return {"hue": hue, "saturation": saturation, "lightness": lightness, "result": result}
    
    async def _adjust_color_balance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """カラーバランスを調整する"""
        shadows = params.get("shadows", [0, 0, 0])
        midtones = params.get("midtones", [0, 0, 0])
        highlights = params.get("highlights", [0, 0, 0])
        preserve_luminosity = params.get("preserveLuminosity", True)
        
        script = f"""
        // カラーバランス調整（シャドウ）
        var cbShadowDesc = new ActionDescriptor();
        var cbShadowAdjDesc = new ActionDescriptor();
        cbShadowAdjDesc.putInteger(charIDToTypeID('Cyn '), {shadows[0]});
        cbShadowAdjDesc.putInteger(charIDToTypeID('Mgnt'), {shadows[1]});
        cbShadowAdjDesc.putInteger(charIDToTypeID('Ylw '), {shadows[2]});
        cbShadowAdjDesc.putBoolean(charIDToTypeID('Lmnc'), {str(preserve_luminosity).lower()});
        cbShadowDesc.putObject(charIDToTypeID('With'), charIDToTypeID('ClrB'), cbShadowAdjDesc);
        cbShadowDesc.putEnumerated(charIDToTypeID('Tone'), charIDToTypeID('TnRg'), charIDToTypeID('Shdw'));
        executeAction(charIDToTypeID('ClrB'), cbShadowDesc, DialogModes.NO);
        
        // カラーバランス調整（ミッドトーン）
        var cbMidtoneDesc = new ActionDescriptor();
        var cbMidtoneAdjDesc = new ActionDescriptor();
        cbMidtoneAdjDesc.putInteger(charIDToTypeID('Cyn '), {midtones[0]});
        cbMidtoneAdjDesc.putInteger(charIDToTypeID('Mgnt'), {midtones[1]});
        cbMidtoneAdjDesc.putInteger(charIDToTypeID('Ylw '), {midtones[2]});
        cbMidtoneAdjDesc.putBoolean(charIDToTypeID('Lmnc'), {str(preserve_luminosity).lower()});
        cbMidtoneDesc.putObject(charIDToTypeID('With'), charIDToTypeID('ClrB'), cbMidtoneAdjDesc);
        cbMidtoneDesc.putEnumerated(charIDToTypeID('Tone'), charIDToTypeID('TnRg'), charIDToTypeID('Mdtn'));
        executeAction(charIDToTypeID('ClrB'), cbMidtoneDesc, DialogModes.NO);
        
        // カラーバランス調整（ハイライト）
        var cbHighlightDesc = new ActionDescriptor();
        var cbHighlightAdjDesc = new ActionDescriptor();
        cbHighlightAdjDesc.putInteger(charIDToTypeID('Cyn '), {highlights[0]});
        cbHighlightAdjDesc.putInteger(charIDToTypeID('Mgnt'), {highlights[1]});
        cbHighlightAdjDesc.putInteger(charIDToTypeID('Ylw '), {highlights[2]});
        cbHighlightAdjDesc.putBoolean(charIDToTypeID('Lmnc'), {str(preserve_luminosity).lower()});
        cbHighlightDesc.putObject(charIDToTypeID('With'), charIDToTypeID('ClrB'), cbHighlightAdjDesc);
        cbHighlightDesc.putEnumerated(charIDToTypeID('Tone'), charIDToTypeID('TnRg'), charIDToTypeID('Hghl'));
        executeAction(charIDToTypeID('ClrB'), cbHighlightDesc, DialogModes.NO);
        
        "カラーバランスを調整しました";
        """
        result = await self.bridge.execute_script(script)
        return {
            "shadows": shadows,
            "midtones": midtones,
            "highlights": highlights,
            "preserveLuminosity": preserve_luminosity,
            "result": result
        }
    
    async def _adjust_vibrance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """自然な彩度を調整する"""
        vibrance = params.get("vibrance", 0)
        saturation = params.get("saturation", 0)
        
        script = f"""
        // 自然な彩度調整
        var vibranceDesc = new ActionDescriptor();
        var vibranceAdjDesc = new ActionDescriptor();
        vibranceAdjDesc.putInteger(stringIDToTypeID('vibrance'), {vibrance});
        vibranceAdjDesc.putInteger(stringIDToTypeID('saturation'), {saturation});
        vibranceDesc.putObject(charIDToTypeID('With'), stringIDToTypeID('vibrance'), vibranceAdjDesc);
        executeAction(stringIDToTypeID('vibrance'), vibranceDesc, DialogModes.NO);
        "自然な彩度を調整しました";
        """
        result = await self.bridge.execute_script(script)
        return {"vibrance": vibrance, "saturation": saturation, "result": result}
    
    async def _adjust_white_balance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ホワイトバランスを調整する"""
        temperature = params.get("temperature", 0)
        tint = params.get("tint", 0)
        
        script = f"""
        // ホワイトバランス調整
        var wbDesc = new ActionDescriptor();
        var wbAdjDesc = new ActionDescriptor();
        wbAdjDesc.putInteger(stringIDToTypeID('temperature'), {temperature});
        wbAdjDesc.putInteger(stringIDToTypeID('tint'), {tint});
        wbDesc.putObject(charIDToTypeID('With'), stringIDToTypeID('cameraRAW'), wbAdjDesc);
        executeAction(stringIDToTypeID('cameraRAW'), wbDesc, DialogModes.NO);
        "ホワイトバランスを調整しました";
        """
        result = await self.bridge.execute_script(script)
        return {"temperature": temperature, "tint": tint, "result": result}
    
    async def _adjust_shadows_highlights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """シャドウ・ハイライトを調整する"""
        shadows = params.get("shadows", 0)
        highlights = params.get("highlights", 0)
        
        script = f"""
        // シャドウ・ハイライト調整
        var shDesc = new ActionDescriptor();
        var shAdjDesc = new ActionDescriptor();
        shAdjDesc.putInteger(stringIDToTypeID('shadowAmount'), {shadows});
        shAdjDesc.putInteger(stringIDToTypeID('highlightAmount'), {highlights});
        shDesc.putObject(charIDToTypeID('With'), stringIDToTypeID('shadowsHighlights'), shAdjDesc);
        executeAction(stringIDToTypeID('shadowsHighlights'), shDesc, DialogModes.NO);
        "シャドウ・ハイライトを調整しました";
        """
        result = await self.bridge.execute_script(script)
        return {"shadows": shadows, "highlights": highlights, "result": result}
    
    async def _apply_filter(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """フィルターを適用する"""
        filter_type = params.get("filterType", "")
        filter_params = params.get("filterParams", {})
        
        # フィルタータイプに応じたスクリプトを生成
        if filter_type == "gaussianBlur":
            radius = filter_params.get("radius", 5.0)
            script = f"""
            // ガウスぼかし
            var gbDesc = new ActionDescriptor();
            gbDesc.putUnitDouble(charIDToTypeID('Rds '), charIDToTypeID('#Pxl'), {radius});
            executeAction(charIDToTypeID('GsnB'), gbDesc, DialogModes.NO);
            "ガウスぼかし（半径: {radius}px）を適用しました";
            """
        elif filter_type == "sharpen":
            amount = filter_params.get("amount", 50)
            script = f"""
            // シャープ
            var sharpDesc = new ActionDescriptor();
            sharpDesc.putInteger(charIDToTypeID('Amnt'), {amount});
            executeAction(charIDToTypeID('Shrp'), sharpDesc, DialogModes.NO);
            "シャープ（量: {amount}）を適用しました";
            """
        elif filter_type == "unsharpMask":
            amount = filter_params.get("amount", 50)
            radius = filter_params.get("radius", 1.0)
            threshold = filter_params.get("threshold", 0)
            script = f"""
            // アンシャープマスク
            var usmDesc = new ActionDescriptor();
            usmDesc.putInteger(charIDToTypeID('Amnt'), {amount});
            usmDesc.putUnitDouble(charIDToTypeID('Rds '), charIDToTypeID('#Pxl'), {radius});
            usmDesc.putInteger(charIDToTypeID('Thsh'), {threshold});
            executeAction(charIDToTypeID('UnsM'), usmDesc, DialogModes.NO);
            "アンシャープマスク（量: {amount}, 半径: {radius}px, しきい値: {threshold}）を適用しました";
            """
        else:
            # 未知のフィルタータイプ
            script = f"""
            "未知のフィルタータイプ: {filter_type}";
            """
        
        result = await self.bridge.execute_script(script)
        return {"filterType": filter_type, "filterParams": filter_params, "result": result}
    
    async def _create_adjustment_layer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """調整レイヤーを作成する"""
        layer_type = params.get("layerType", "")
        layer_params = params.get("layerParams", {})
        
        # レイヤータイプに応じたスクリプトを生成
        if layer_type == "curves":
            script = """
            // カーブ調整レイヤー
            var curvesLayerDesc = new ActionDescriptor();
            var layerDesc = new ActionDescriptor();
            var adjDesc = new ActionDescriptor();
            
            layerDesc.putObject(charIDToTypeID('Type'), charIDToTypeID('Crvs'), adjDesc);
            curvesLayerDesc.putObject(charIDToTypeID('Nw  '), charIDToTypeID('AdjL'), layerDesc);
            executeAction(charIDToTypeID('Mk  '), curvesLayerDesc, DialogModes.NO);
            "カーブ調整レイヤーを作成しました";
            """
        elif layer_type == "levels":
            script = """
            // レベル調整レイヤー
            var levelsLayerDesc = new ActionDescriptor();
            var layerDesc = new ActionDescriptor();
            var adjDesc = new ActionDescriptor();
            
            layerDesc.putObject(charIDToTypeID('Type'), charIDToTypeID('Lvls'), adjDesc);
            levelsLayerDesc.putObject(charIDToTypeID('Nw  '), charIDToTypeID('AdjL'), layerDesc);
            executeAction(charIDToTypeID('Mk  '), levelsLayerDesc, DialogModes.NO);
            "レベル調整レイヤーを作成しました";
            """
        elif layer_type == "hueSaturation":
            script = """
            // 色相・彩度調整レイヤー
            var hslLayerDesc = new ActionDescriptor();
            var layerDesc = new ActionDescriptor();
            var adjDesc = new ActionDescriptor();
            
            layerDesc.putObject(charIDToTypeID('Type'), charIDToTypeID('HStr'), adjDesc);
            hslLayerDesc.putObject(charIDToTypeID('Nw  '), charIDToTypeID('AdjL'), layerDesc);
            executeAction(charIDToTypeID('Mk  '), hslLayerDesc, DialogModes.NO);
            "色相・彩度調整レイヤーを作成しました";
            """
        else:
            # 未知の調整レイヤータイプ
            script = f"""
            "未知の調整レイヤータイプ: {layer_type}";
            """
        
        result = await self.bridge.execute_script(script)
        return {"layerType": layer_type, "layerParams": layer_params, "result": result}
    
    async def _run_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """アクションを実行する"""
        action_set = params.get("set", "")
        action_name = params.get("action", "")
        
        if not action_set or not action_name:
            return {"error": "アクションセットとアクション名が必要です"}
        
        result = await self.bridge.run_action(action_set, action_name)
        return {"set": action_set, "action": action_name, "result": result}
    
    async def _execute_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """JavaScriptを実行する"""
        script = params.get("script", "")
        
        if not script:
            return {"error": "スクリプトが指定されていません"}
        
        result = await self.bridge.execute_script(script)
        return {"script": script, "result": result}
    
    async def _execute_custom_command(self, cmd_type: str, cmd_params: Dict[str, Any]) -> Dict[str, Any]:
        """カスタムコマンドを実行する"""
        # パラメータをJSON文字列に変換
        params_json = json.dumps(cmd_params)
        
        # JavaScriptコードを生成
        script = f"""
        // カスタムコマンド: {cmd_type}
        var params = {params_json};
        var result = "カスタムコマンド '{cmd_type}' を実行しました";
        
        // パラメータの処理
        for (var key in params) {{
            result += "\\n - " + key + ": " + params[key];
        }}
        
        result;
        """
        
        result = await self.bridge.execute_script(script)
        return {"commandType": cmd_type, "params": cmd_params, "result": result}